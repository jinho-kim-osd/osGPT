from typing import Optional, List
import re

from forge.sdk import (
    Agent,
    Step,
    StepRequestBody,
    Workspace,
    ForgeLogger,
    Task,
    TaskRequestBody,
    PromptEngine,
    Message,
)
from forge.db import ForgeDatabase
from .agent import ForgeAgent
from .user_proxy_agent import UserProxyAgent

logger = ForgeLogger(__name__)


TERMINATION_WORD = "<TERMINATE>"
RECIPIENT_MATCHING_PATTERN = "@(\w+)"


class MasterAgent(ForgeAgent):
    def __init__(
        self,
        database: ForgeDatabase,
        workspace: Workspace,
        name: str = "Master",
        ability_names: Optional[List[str]] = None,
    ):
        self.user_agent = UserProxyAgent(
            database, workspace, name="User", ability_names=["read_file", "list_files"]
        )
        self.agents: List[ForgeAgent] = [
            self.user_agent,
            ForgeAgent(
                database,
                workspace,
                name="Engineer",
                ability_names=[
                    "run_python_code",
                    "read_file",
                    "list_files",
                ],
            ),
            ForgeAgent(
                database,
                workspace,
                name="Task Manager",
                ability_names=["read_file", "list_files"],
            ),
        ]
        super().__init__(database, workspace, name, ability_names)
        self.prompt_engine = PromptEngine("master")

    def _load_system_prompt(self, **kwargs) -> PromptEngine:
        return self.prompt_engine.load_prompt(
            "system-message",
            name=self.name,
            agents=self.agents,
            **kwargs,
        )

    @property
    def agent_handles(self) -> List[str]:
        return [agent.handle for agent in self.agents]

    @property
    def agent_names(self) -> List[str]:
        return [agent.name for agent in self.agents]

    def agent_by_name(self, name: str) -> ForgeAgent:
        return self.agents[self.agent_names.index(name)]

    def agent_by_handle(self, handle: str) -> ForgeAgent:
        for agent in self.agents:
            if agent.handle == handle:
                return agent
        raise ValueError(f"Not found {handle}")

    async def select_next_agent(
        self,
        task: Task,
        step: Step,
    ) -> Optional[ForgeAgent]:
        select_speaker_suffix_prompt = self.prompt_engine.load_prompt(
            "system-message-suffix",
            agents=self.agents,
            agent_handles=self.agent_handles,
        )

        formatted_messages = [
            Message(
                content=f"{message.sender_id}: {message.content}",
                sender_id=message.sender_id,
                recipient_id=message.recipient_id,
            )
            for message in self.chat_messages[self.handle]
        ]
        speaker_id = await self.chat_completion_request(
            task.task_id,
            step.step_id,
            [
                self.system_message,
                *formatted_messages,
                Message(
                    content=select_speaker_suffix_prompt,
                    sender_id=self.handle,
                    recipient_id=self.handle,
                ),
            ],
            sender=self,
        )

        speaker_id = speaker_id.replace("'", "")
        if speaker_id in [TERMINATION_WORD, "TERMINATE"]:
            return None
        return self.agent_by_handle(speaker_id)

    async def create_task(self, task_request: TaskRequestBody) -> Task:
        return await super().create_task(task_request)

    def reset(self):
        super().reset()
        for agent in self.agents:
            agent.reset()

    async def next_step(self, task_id: str) -> Optional[Step]:
        steps, _ = await self.db.list_steps(task_id, per_page=100)
        _, pending_steps = self._categorize_steps(steps)
        if pending_steps:
            return pending_steps.pop(0)
        return None

    async def execute_step(self, task_id: str, step_request: StepRequestBody) -> Step:
        """Execute a task step and update its status and output."""
        task = await self.db.get_task(task_id)
        all_steps, _ = await self.db.list_steps(task_id, per_page=100)
        step = await self.next_step(task_id)
        logger.info("Next Step : " + str(step))

        additional_input = step_request.additional_input or {}
        is_whisper_mode = additional_input.get("is_whisper_mode", False)
        step = await self.create_step(
            task_id,
            step_request.input,
            f"step_{len(all_steps) + 1}",
        )
        step = await self.db.update_step(task_id, step.step_id, "running")

        # Add message Only if user input exists
        if step_request.input:
            sender = self.user_agent
            recipient_agents = []
            # TODO: Resolve duplicated initial message
            message = Message(
                content=step_request.input,
                sender_id=sender.handle,
                recipient_id=self.handle,
            )
            self.chat_messages[self.handle].append(message)

            if is_whisper_mode:
                recipient: ForgeAgent = await self.select_next_agent(task, step)
                recipient_agents.append(recipient)
            else:
                recipient_agents.extend(
                    [agent for agent in self.agents if agent != sender]
                )

            for recipient in recipient_agents:
                message = Message(
                    content=step_request.input,
                    sender_id=sender.handle,
                    recipient_id=recipient.handle,
                )
                await self.user_agent.send_message(
                    task_id,
                    message.content,
                    recipient,
                    step.step_id,
                    request_reply=False,
                )

        speaker: ForgeAgent = await self.select_next_agent(task, step)
        if speaker is None:
            logger.info("Step successfully completed.")
            step = await self.db.update_step(
                task_id,
                step.step_id,
                "completed",
                output=TERMINATION_WORD,
                additional_input={"speaker": self.handle},
            )
            step.is_last = True
            return step

        last_message = speaker.get_last_message()
        logger.info(
            f"Last Message [{last_message.sender_id} -> {last_message.recipient_id}]: {last_message.content}"
        )
        sender = self.agent_by_handle(last_message.sender_id)
        reply_content = await speaker.reply_message(
            task_id=task_id,
            step_id=step.step_id,
            messages=speaker.all_chat_messages,
            sender=sender,
        )

        # Extract Recipient IDs from reply message
        recipient_ids = re.findall(RECIPIENT_MATCHING_PATTERN, reply_content)
        if recipient_ids is None:
            recipient_ids = self.agent_handles

        for recipient_id in recipient_ids:
            recipient = self.agent_by_handle(recipient_id)
            speaker_message = Message(
                content=reply_content,
                sender_id=speaker.handle,
                recipient_id=recipient.handle,
            )
            logger.info(
                f"Reply Message [{speaker.name} -> {str(recipient.name)}]: {speaker_message.content}"
            )
            await speaker.send_message(
                task_id=task_id,
                content=speaker_message.content,
                recipient=recipient,
                step_id=step.step_id,
                request_reply=False,
            )
            self.chat_messages[self.handle].append(speaker_message)

        # The speaker sends the message without requesting a reply
        await self.receive(task_id, reply_content, sender, step.step_id, False)
        step = await self.db.update_step(
            task_id,
            step.step_id,
            "completed",
            output=reply_content,
            additional_input={
                "last_sender": sender.handle,
                "speaker": speaker.handle,
            },
        )
        return step
