import json
import pprint
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
)
from forge.db import ForgeDatabase
from .actions import (
    PlanStepsAction,
    ExecuteStepAction,
    RequestChatAction,
    AnswerAction,
    RunAbilityAction,
    CreatePlannedStepsAction,
)
from .utils import (
    gpt4_chat_completion_request,
    extract_top_level_json,
    replace_prompt_placeholders,
)

logger = ForgeLogger(__name__)


class ForgeAgent(Agent):
    MAX_RETRIES = 5

    def __init__(self, database: ForgeDatabase, workspace: Workspace):
        super().__init__(database, workspace)
        self.chat_history = []
        self.action_history = []
        self.prompt_engine = PromptEngine("os-gpt")

    async def _create_planning_step(self, task: Task) -> Step:
        self.clear_chat_history()
        step = await self.create_step(task_id=task.task_id, input=task.input)
        step.status = Status.running

        abilities = self.abilities.list_abilities_for_prompt()
        files = self.workspace.list(task.task_id, "/")
        system_prompt = self.prompt_engine.load_prompt(
            "plan-system-message", abilities=abilities, files=files
        )
        user_prompt = self.prompt_engine.load_prompt(
            "plan-user-message", input=task.input
        )
        await self.add_chat(task.task_id, "system", system_prompt)
        await self.add_chat(task.task_id, "user", user_prompt)
        return step

    async def _initialize_step(self, task: Task, step: Step) -> Step:
        self.clear_chat_history()
        steps, _ = await self.db.list_steps(task.task_id, per_page=100)
        previous_steps, _ = self._categorize_steps(steps)

        step = await self.db.update_step(
            task_id=task.task_id,
            step_id=step.step_id,
            status=Status.running.value,
            additional_input={step.name: step.json() for step in previous_steps},
        )

        abilities = self.abilities.list_abilities_for_prompt()
        files = self.workspace.list(task.task_id, "/")
        system_prompt = self.prompt_engine.load_prompt(
            "complete-system-message", abilities=abilities, files=files
        )
        await self.add_chat(task.task_id, "system", system_prompt)

        user_prompt = self.prompt_engine.load_prompt(
            "complete-user-message",
            input=step.input,
            abilities=abilities,
            # previous_steps=previous_steps,
        )
        # Replace placeholders with actual output from the specified steps
        user_prompt = replace_prompt_placeholders(
            user_prompt, **{step.name: step for step in previous_steps}
        )
        await self.add_chat(task.task_id, "user", user_prompt)
        return step

    async def _request_chat(self, task: Task, step: Step) -> Dict[str, Any]:
        for _ in range(self.MAX_RETRIES):
            # logger.info(str(self.chat_history))
            response = await gpt4_chat_completion_request(self.chat_history)
            await self.add_chat(task.task_id, "assistant", content=response)
            logger.info("Request Chat Reponse: " + response)

            try:
                try:
                    parsed_output = extract_top_level_json(response)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Could not parse JSON. error: {e}")
                return parsed_output
            except ValueError as e:
                error_message = str(e)
                logger.error(f"Error: {error_message}")
                await self.add_chat(
                    task.task_id,
                    "user",
                    "Reminder to always use the exact format when responding.",
                )

        logger.error("Max retries reached. Unable to parse output.")
        raise Exception("Unable to parse output after max retries.")

    async def _create_planned_steps(
        self, task: Task, step: Step, planned_steps: List[Dict[str, Any]]
    ) -> str:
        for planned_step in planned_steps:
            await self.create_step(
                task_id=task.task_id,
                input=planned_step["input"]
                + "\n\n"
                + f"# Original Plan:\n\n{str(planned_step)}",
                name=planned_step["name"],
            )
        observation = str(planned_steps)
        return observation

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
        return observation

    async def _answer(
        self, task: Task, step: Step, observation: Optional[str] = None
    ) -> Dict[str, Any]:
        last_assistant_message = next(
            (
                msg["content"]
                for msg in reversed(self.chat_history)
                if msg["role"] == "assistant"
            ),
            None,
        )
        previous_parsed_output = extract_top_level_json(last_assistant_message)
        previous_parsed_output["thoughts"]["observation"] = observation
        await self.add_chat(task.task_id, "assistant", str(previous_parsed_output))
        await self.add_chat(
            task.task_id,
            "user",
            "Fill the final answer in the exact format based on the observation. If the observation is webpage results, return it directly",
        )

        parsed_output = await self._request_chat(task, step)
        parsed_output["thoughts"]["observation"] = observation
        logger.info(f"Final message received: {str(parsed_output)}")
        await self.add_chat(task.task_id, "assistant", str(parsed_output))

        step = await self.db.update_step(
            task_id=task.task_id,
            step_id=step.step_id,
            status=Status.completed.value,
            output=str(parsed_output),
        )
        # step.artifacts = artifacts

        # is_plan = previous_parsed_output.get("plan", False) is not False
        is_finished = (
            previous_parsed_output.get("ability", {}).get("name", None) == "finish"
        )
        step.is_last = is_finished
        return step

    async def execute_step(self, task_id: str, step_request: StepRequestBody) -> Step:
        """Execute a task step and update its status and output."""
        task = await self.db.get_task(task_id)

        steps, _ = await self.db.list_steps(task_id, per_page=100)
        previous_steps, pending_steps = self._categorize_steps(steps)

        is_plan = len(pending_steps) == 0
        if is_plan:
            action = PlanStepsAction(task)
        else:
            # TODO: human-editing using step_request
            step = pending_steps[0]
            logger.info("Execute Step!: " + str(step.dict()))
            action = ExecuteStepAction(task, step)

        step: Step = await self._handle_action(action)
        return step

    async def _handle_action(self, action: Action, step: Optional[Step] = None) -> Any:
        logger.info("Action: " + str(action.name))
        self.action_history.append(action)
        if isinstance(action, PlanStepsAction):
            step = await self._create_planning_step(action.task)
            step_or_action = RequestChatAction(action.task, step)
            while isinstance(step_or_action, Action):
                step_or_action = await self._handle_action(step_or_action, step)
            step = step_or_action
            return step
        elif isinstance(action, ExecuteStepAction):
            step = await self._initialize_step(action.task, action.step)
            step_or_action = RequestChatAction(action.task, step)
            while isinstance(step_or_action, Action):
                step_or_action = await self._handle_action(step_or_action, step)
            step = step_or_action
            return step
        elif isinstance(action, RequestChatAction):
            parsed_output = await self._request_chat(action.task, action.step)
            if parsed_output.get("plan", None):
                planned_steps = parsed_output["plan"]
                return CreatePlannedStepsAction(action.task, step, planned_steps)
            elif parsed_output.get("ability", None):
                ability = parsed_output["ability"]
                return RunAbilityAction(action.task, step, ability)
            else:
                raise NotImplementedError
                # return AnswerAction(action.task, step)
        elif isinstance(action, CreatePlannedStepsAction):
            observation = await self._create_planned_steps(
                action.task, action.step, action.planned_steps
            )
            return AnswerAction(action.task, action.step, observation)
        elif isinstance(action, RunAbilityAction):
            observation = await self._run_ability(
                action.task, action.step, action.ability
            )
            return AnswerAction(action.task, action.step, observation)
        # elif isinstance(action, EvaluateAction):
        #     observation = await self._run_ability(action)
        #     return step
        # elif isinstance(action, GenerateReflectionAction):
        #     observation = await self._run_ability(action)
        #     return step
        elif isinstance(action, AnswerAction):
            step = await self._answer(action.task, action.step, action.observation)
            return step
        else:
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

    async def create_task(self, task_request: TaskRequestBody) -> Task:
        task = await super().create_task(task_request)
        logger.info(
            f"📦 Task created: {task.task_id} input: {task.input[:40]}{'...' if len(task.input) > 40 else ''}"
        )
        return task

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

    async def add_chat(self, task_id: str, role: str, content: str, **kwargs):
        await self.db.add_chat_message(task_id, role, content)
        self.chat_history.append({"role": role, "content": content, **kwargs})

    async def add_action(self, task_id: str, name: str, args: dict):
        action = await self.db.create_action(task_id, name, args)
        return action

    def clear_chat_history(self):
        self.chat_history = []
