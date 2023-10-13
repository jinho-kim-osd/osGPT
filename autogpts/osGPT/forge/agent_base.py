import json
from abc import abstractmethod
from collections import defaultdict
from typing import Optional, Tuple, List, Any, Union, Literal, Dict

from forge.sdk import (
    Agent,
    Step,
    StepRequestBody,
    Workspace,
    ForgeLogger,
    Task,
    TaskRequestBody,
    Artifact,
    PromptEngine,
    Status,
    Action,
    Message,
)
from forge.db import ForgeDatabase
from .ability_registry import ForgeAbilityRegister
from .utils import (
    gpt4_chat_completion_request,
    extract_top_level_json,
    replace_prompt_placeholders,
)

logger = ForgeLogger(__name__)


class ForgeAgentBase(Agent):
    MAX_RETRIES = 5

    def __init__(
        self,
        database: ForgeDatabase,
        workspace: Workspace,
        name: str,
        ability_names: Optional[List[str]] = None,
        system_message: Optional[str] = None,
        use_prompt_engine: bool = True,
    ):
        self.db = database
        self.workspace = workspace
        self.abilities = ForgeAbilityRegister(self, ability_names)
        self.name = name
        self.chat_messages: List[Message] = defaultdict(list)
        self.prompt_engine = PromptEngine(self.name)
        self.use_prompt_engine = use_prompt_engine
        self._system_message = system_message

    @property
    def openai_chat_messages(
        self, actor: Optional["ForgeAgentBase"] = None
    ) -> List[Dict[str, str]]:
        if actor is None:
            actor = self
        return [message.to_openai_message(actor.name) for message in self.chat_messages]

    # @abstractmethod
    # def step(self, task: Task | None, step: Step | None):
    #     step.additional_input.get("sender", None)
    #     step.additional_input.get("recipient", None)
    #     step.additional_input.get("action", None)
    #     step.additional_input.get("ability", None)

    #     if step:
    #         step_handler = self.get_step_handler(step)
    #         step_handler.apply_action()
    #     else:
    #         self.create_step()
    #     raise NotImplementedError

    @property
    def system_message(self, **kwargs) -> Message:
        if self._system_message:
            content = self._system_message
        else:
            content = self.prompt_engine.load_prompt("system-message", **kwargs)
        return Message(content=content, sender_id=self.name, recipient_id=self.name)

    async def update_system_message(self, content: str):
        self._system_message = content

    def get_last_message(self, conversation_id: Optional[str] = None) -> Message:
        if conversation_id is None:
            n_conversations = len(self.chat_messages)
            if n_conversations == 0:
                return None
            if n_conversations == 1:
                for conversation in self.chat_messages.values():
                    return conversation[-1]
            raise ValueError
        return self.chat_messages[conversation_id][-1]

    async def send_message(
        self,
        task_id: str,
        content: str,
        recipient: Optional["ForgeAgentBase"],
        step_id: Optional[str] = None,
        request_reply: bool = False,
    ) -> Optional[Any]:
        # TODO: Update db for recipient
        message = Message(
            content=content, sender_id=self.name, recipient_id=recipient.name
        )
        await self._add_message(message, recipient.name, task_id, step_id)
        await recipient.receive(task_id, content, self, step_id, request_reply)

        if request_reply:
            return self.reply_message(task_id, step_id)

    async def receive(
        self,
        task_id: str,
        content: str,
        sender: "ForgeAgentBase",
        step_id: Optional[str] = None,
        request_reply: bool = False,
    ) -> None:
        message = Message(
            content=content, sender_id=sender.name, recipient_id=self.name
        )
        await self._add_message(message, sender.name, task_id, step_id)
        if request_reply:
            reply = await self.reply_message(
                task_id,
                step_id,
                messages=self.chat_messages[sender.name],
                sender=sender,
            )
            if reply:
                self.send_message(task_id, reply, sender, step_id=step_id)

    async def reply_message(
        self,
        task_id: str,
        step_id: Optional[str] = None,
        messages: Optional[List[Dict]] = None,
        sender: Optional["ForgeAgentBase"] = None,
        formatter: Optional[str] = None,
    ) -> Any:
        if messages is None:
            messages = self.chat_messages[sender.name]

        for _ in range(self.MAX_RETRIES):
            response = await self.chat_completion_request(
                [self.system_message] + messages, sender
            )

            if formatter == "json":
                try:
                    response = extract_top_level_json(response)
                except ValueError as e:
                    error_message = str(e)
                    logger.error(f"Error: {error_message}")
            logger.info(f"Request Chat Reponse[{self.name}]: " + str(response))
            return response

    async def chat_completion_request(
        self,
        messages: Optional[List[Message]] = None,
        sender: Optional["ForgeAgentBase"] = None,
    ) -> str:
        if messages is None:
            messages = self.chat_messages[sender.name]
        logger.info(f"Messages[{self.name}]: " + str(messages))
        openai_messages = [message.to_openai_message(self.name) for message in messages]
        logger.info(f"OpenAI Messages[{self.name}]: " + str(openai_messages))

        ## TODO: determine_function_call
        response = await gpt4_chat_completion_request(openai_messages)
        logger.info(f"Response[{self.name}]: " + str(response))
        return response

    async def check_ability_to_run(
        self,
        messages: Optional[List[Message]] = None,
        sender: Optional["ForgeAgentBase"] = None,
    ):
        openai_messages = [message.to_openai_message(self.name) for message in messages]
        ...

    async def _run_ability(
        self, task: Task, step: Step, ability: Dict[str, Any]
    ) -> str:
        name = ability["name"]
        args = ability.get("args", {})
        logger.info(f"Ability: {name}({str(args)})")

        observation = await self.abilities.run_ability(task.task_id, name, **args)
        if isinstance(observation, Artifact):
            await self.db.update_artifact(
                artifact_id=observation.artifact_id, step_id=step.step_id
            )
            observation = observation.dict(exclude_none=True)
        elif isinstance(observation, dict):
            artifacts: List[Artifact] = observation.pop("artifacts", [])
            for artifact in artifacts:
                await self.db.update_artifact(
                    artifact_id=artifact.artifact_id, step_id=step.step_id
                )
        elif isinstance(observation, list):
            for item in observation:
                if isinstance(item, Artifact):
                    await self.db.update_artifact(
                        artifact_id=item.artifact_id, step_id=step.step_id
                    )
                    index = observation.index(item)
                    observation[index] = item.dict(exclude_none=True)
            observation = str(observation)
        return observation

    @abstractmethod
    async def execute_step(self, task_id: str, step_request: StepRequestBody) -> Step:
        raise NotImplementedError

    @abstractmethod
    async def _handle_action(
        self, action: Action, step: Optional[Step] = None
    ) -> Step | Action:
        raise NotImplementedError

    def _categorize_steps(self, steps: List[Step]) -> Tuple[List[Step], List[Step]]:
        previous_steps = []
        pending_steps = []
        for step in steps:
            if step.status == Status.created:
                pending_steps.append(step)
            elif step.status == Status.completed:
                previous_steps.append(step)
        return previous_steps, pending_steps

    async def create_step(
        self,
        task_id: str,
        input: str,
        name: Optional[str] = None,
        additional_input: Optional[dict] = None,
    ) -> Step:
        if name is None:
            name = input
        step_request = StepRequestBody(
            name=name, input=input, additional_input=additional_input
        )
        return await self.db.create_step(
            task_id=task_id, input=step_request, additional_input=additional_input
        )

    async def _add_message(
        self,
        message: Message,
        conversation_id: str,
        task_id: str,
        step_id: Optional[str] = None,
    ):
        await self.db.add_chat_message(
            task_id, message.content, step_id, message.sender_id, message.recipient_id
        )
        self.chat_messages[conversation_id].append(message)

    async def _add_action(self, task_id: str, name: str, args: dict):
        action = await self.db.create_action(task_id, name, args)
        return action

    def reset(self):
        self.chat_messages = defaultdict(list)
