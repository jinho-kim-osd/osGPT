from typing import Optional, List

from forge.sdk import (
    Agent,
    Step,
    StepRequestBody,
    Workspace,
    ForgeLogger,
    Task,
    TaskRequestBody,
    PromptEngine,
    Artifact,
    Message,
)
from forge.db import ForgeDatabase
from .agent import ForgeAgent

logger = ForgeLogger(__name__)


TERMINATION_WORD = "<TERMINATE>"


class MasterAgent(ForgeAgent):
    def __init__(
        self,
        database: ForgeDatabase,
        workspace: Workspace,
        name: str = "Master",
        ability_names: Optional[List[str]] = None,
    ):
        self.user_agent = ForgeAgent(
            database,
            workspace,
            name="User",
        )
        self.agents: List[ForgeAgent] = [
            self.user_agent,
            ForgeAgent(
                database,
                workspace,
                name="Engineer",
                ability_names=["run_python_code", "read_file", "list_files"],
            ),
            ForgeAgent(
                database,
                workspace,
                name="TaskManager",
            ),
        ]
        self.prompt_engine = PromptEngine("master")
        system_message = self.prompt_engine.load_prompt(
            "system-message", agents=self.agents, agent_names=self.agent_names
        )
        super().__init__(database, workspace, name, ability_names, system_message)

    @property
    def agent_names(self) -> List[str]:
        return [agent.name for agent in self.agents]

    def agent_by_name(self, name: str) -> ForgeAgent:
        return self.agents[self.agent_names.index(name)]

    def next_agent(self, agent: Agent) -> ForgeAgent:
        return self.agents[(self.agent_names.index(agent.name) + 1) % len(self.agents)]

    async def select_speaker(
        self,
        task: Task,
        step: Step,
        last_speaker: ForgeAgent,
    ) -> Optional[ForgeAgent]:
        """Select the next speaker."""
        # select_speaker_prompt = self.prompt_engine.load_prompt(
        #     "system-message", agents=self.agents, agent_names=self.agent_names
        # )
        # await self.update_system_message(select_speaker_prompt)

        select_speaker_suffix_prompt = self.prompt_engine.load_prompt(
            "system-message-suffix", agents=self.agents, agent_names=self.agent_names
        )
        agent_name = await self.chat_completion_request(
            task.task_id,
            step.step_id,
            [
                self.system_message,
                *self.chat_messages[self.name],
                Message(
                    content=select_speaker_suffix_prompt,
                    sender_id=self.name,
                    recipient_id=self.name,
                ),
            ],
            sender=self,
        )

        agent_name = agent_name.replace("'", "")
        if agent_name == TERMINATION_WORD:
            return None
        try:
            return self.agent_by_name(agent_name)
        except ValueError as e:
            logger.error(f"Error: {e}")
            return self.next_agent(last_speaker)

    async def create_task(self, task_request: TaskRequestBody) -> Task:
        super().reset()
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

        step = await self.create_step(
            task_id,
            step_request.input,
            f"step_{len(all_steps) + 1}",
        )
        step = await self.db.update_step(task_id, step.step_id, "running")

        if step_request.input:
            sender_id = self.user_agent.name
            message = Message(
                content=step_request.input,
                sender_id=sender_id,
                recipient_id=None,
            )
            self.chat_messages[self.name].append(message)

        message: Message = self.chat_messages[self.name][-1]
        logger.info("Last Message :" + str(message))
        sender_id = message.sender_id
        if sender_id == self.name:
            last_speaker = self
        else:
            last_speaker = self.agent_by_name(sender_id)

        # broadcast the message to all agents except the assignee
        for agent in self.agents:
            if agent != last_speaker:
                await self.send_message(
                    task_id, message.content, agent, step.step_id, request_reply=False
                )

        speaker = await self.select_speaker(task, step, last_speaker=last_speaker)
        if speaker is None:
            logger.info("Terminated!")
            step = await self.db.update_step(
                task_id,
                step.step_id,
                "completed",
                output=TERMINATION_WORD,
                additional_input={"speaker": self.name},
            )
            step.is_last = True
            return step
        logger.info("Speaker :" + str(speaker.name))
        reply = await speaker.reply_message(task_id, step.step_id, sender=self)
        logger.info("Reply :" + str(reply))

        reply_message = Message(
            content=reply,
            sender_id=speaker.name,
            recipient_id=self.name,
        )
        logger.info("Reply Message :" + str(reply_message))
        self.chat_messages[self.name].append(reply_message)  # TODO: Required?

        # The speaker sends the message without requesting a reply
        await speaker.send_message(task_id, reply, self, request_reply=False)
        step = await self.db.update_step(
            task_id,
            step.step_id,
            "completed",
            output=reply,
            additional_input={"speaker": speaker.name},
        )
        return step
