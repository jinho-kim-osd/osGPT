import json
import re
from abc import abstractmethod
from collections import defaultdict
from typing import Optional, Tuple, List, Any, Dict

from forge.sdk import (
    Agent,
    Step,
    StepRequestBody,
    Workspace,
    ForgeLogger,
    Task,
    Artifact,
    PromptEngine,
    Status,
    Message,
)
from forge.db import ForgeDatabase
from .ability_registry import ForgeAbilityRegister
from .utils import gpt4_chat_completion_request, camel_to_snake

logger = ForgeLogger(__name__)

ROLE_MATCHING_PATTERN = "# ROLE\n(.*?)\n# "


class ForgeAgent(Agent):
    MAX_RETRIES = 5

    def __init__(
        self,
        database: ForgeDatabase,
        workspace: Workspace,
        name: str,
        ability_names: Optional[List[str]] = None,
        system_message: Optional[str] = None,
    ):
        self.db = database
        self.workspace = workspace
        self.abilities = ForgeAbilityRegister(self, ability_names)
        self.name = name
        self.chat_messages: List[Message] = defaultdict(list)
        if system_message is None:
            self.prompt_engine = PromptEngine("forge")
            system_message = self.prompt_engine.load_prompt(
                camel_to_snake(self.name), name=self.name
            )

        self._system_message = system_message

    @property
    def openai_chat_messages(
        self, actor: Optional["ForgeAgent"] = None
    ) -> List[Dict[str, str]]:
        if actor is None:
            actor = self
        return [message.to_openai_message(actor.name) for message in self.chat_messages]

    @property
    def system_message(self) -> Message:
        return Message(
            content=self._system_message, sender_id=self.name, recipient_id=self.name
        )

    @property
    def role(self) -> Optional[str]:
        role_content = re.search(
            ROLE_MATCHING_PATTERN, self.system_message.content, re.DOTALL
        )
        if role_content:
            return role_content.group(1).strip()
        return None

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
        recipient: Optional["ForgeAgent"],
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
        sender: "ForgeAgent",
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
        sender: Optional["ForgeAgent"] = None,
    ) -> Any:
        if messages is None:
            messages = self.chat_messages[sender.name]

        for _ in range(self.MAX_RETRIES):
            task = await self.db.get_task(task_id=task_id)
            response = await self.chat_completion_request(
                task_id,
                step_id,
                [self.system_message] + messages,
                sender,
            )
            logger.info(f"Request Chat Reponse[{self.name}]: " + str(response))
            return response

    async def chat_completion_request(
        self,
        task_id: Optional[str] = None,
        step_id: Optional[str] = None,
        messages: Optional[List[Message]] = None,
        sender: Optional["ForgeAgent"] = None,
    ) -> str:
        import asyncio

        # TODO: Control OpenAI Rate limit
        # asyncio.sleep(12)
        if messages is None:
            messages = self.chat_messages[sender.name]
        logger.info(f"Messages[{self.name}]: " + str(messages))
        openai_messages = [message.to_openai_message(self.name) for message in messages]
        logger.info(f"OpenAI Messages[{self.name}]: " + str(openai_messages))

        functions = self.abilities.list_abilities_for_function_calling()
        response = await gpt4_chat_completion_request(
            openai_messages, functions=functions
        )
        if "function_call" in response:
            response = await self._handle_function_call(
                response, task_id, step_id, openai_messages, sender.name
            )
        logger.info(f"Response[{self.name}]: " + str(response))
        return response["content"]

    async def _handle_function_call(
        self,
        response: Dict[str, Any],
        task_id: Optional[str] = None,
        step_id: Optional[str] = None,
        openai_messages: Optional[List[Dict[str, Any]]] = None,
        conversation_id: Optional[str] = None,
    ) -> str:
        fn_name = response["function_call"]["name"]
        logger.info(f"Debug Function Response[{self.name}]: " + str(response))
        fn_args = json.loads(response["function_call"]["arguments"])
        logger.info(f"Function Calling[{self.name}]: {fn_name}({fn_args})")
        fn_response = await self.abilities.run_ability(task_id, fn_name, **fn_args)
        if isinstance(fn_response, Artifact):
            await self.db.update_artifact(
                artifact_id=fn_response.artifact_id, step_id=step_id
            )
            fn_response = fn_response.dict(exclude_none=True)
        # TODO: find better approach
        elif isinstance(fn_response, dict):
            artifacts: List[Artifact] = fn_response.pop("artifacts", [])
            for artifact in artifacts:
                await self.db.update_artifact(
                    artifact_id=artifact.artifact_id, step_id=step_id
                )
        elif isinstance(fn_response, list):
            for item in fn_response:
                if isinstance(item, Artifact):
                    await self.db.update_artifact(
                        artifact_id=item.artifact_id, step_id=step_id
                    )
                    index = fn_response.index(item)
                    fn_response[index] = item.dict(exclude_none=True)
        logger.info(str(fn_response))
        if fn_response is not None:
            fn_response = str(fn_response)

        logger.info(f"Function Response[{self.name}]: {fn_response}")
        message = Message(
            content=fn_response,
            sender_id=self.name,
            recipient_id=self.name,
            function_call={"name": fn_name, "arguments": fn_args},
        )
        if conversation_id is None:
            conversation_id = self.name
        await self._add_message(message, conversation_id, task_id, step_id)
        openai_messages.append(message.to_openai_message(fn_name))
        response = await gpt4_chat_completion_request(openai_messages)
        return response

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
