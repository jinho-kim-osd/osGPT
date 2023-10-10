import json
import pprint
import re
from typing import Optional, Tuple, List, Any, Union, Literal

from forge.sdk import (
    Agent,
    # AgentDB,
    Step,
    StepRequestBody,
    Workspace,
    ForgeLogger,
    Task,
    TaskRequestBody,
    Artifact,
    PromptEngine,
    chat_completion_request,
    Status,
)
from forge.db import ForgeDatabase, ChatModel
from forge.schemas import AgentThoughts, AgentAction, AgentObservation

logger = ForgeLogger(__name__)
OPENAI_MODEL = "gpt-4"
StepType = Literal["planning", "complete"]


class ForgeAgent(Agent):
    """
    The goal of the Forge is to take care of the boilerplate code so you can focus on
    agent design.

    There is a great paper surveying the agent landscape: https://arxiv.org/abs/2308.11432
    Which I would highly recommend reading as it will help you understand the possabilities.

    Here is a summary of the key components of an agent:

    Anatomy of an agent:
         - Profile
         - Memory
         - Planning
         - Action

    Profile:

    Agents typically perform a task by assuming specific roles. For example, a teacher,
    a coder, a planner etc. In using the profile in the llm prompt it has been shown to
    improve the quality of the output. https://arxiv.org/abs/2305.14688

    Additionally baed on the profile selected, the agent could be configured to use a
    different llm. The possabilities are endless and the profile can be selected selected
    dynamically based on the task at hand.

    Memory:

    Memory is critical for the agent to acculmulate experiences, self-evolve, and behave
    in a more consistent, reasonable, and effective manner. There are many approaches to
    memory. However, some thoughts: there is long term and short term or working memory.
    You may want different approaches for each. There has also been work exploring the
    idea of memory reflection, which is the ability to assess its memories and re-evaluate
    them. For example, condensting short term memories into long term memories.

    Planning:

    When humans face a complex task, they first break it down into simple subtasks and then
    solve each subtask one by one. The planning module empowers LLM-based agents with the ability
    to think and plan for solving complex tasks, which makes the agent more comprehensive,
    powerful, and reliable. The two key methods to consider are: Planning with feedback and planning
    without feedback.

    Action:

    Actions translate the agents decisions into specific outcomes. For example, if the agent
    decides to write a file, the action would be to write the file. There are many approaches you
    could implement actions.

    The Forge has a basic module for each of these areas. However, you are free to implement your own.
    This is just a starting point.
    """

    MAX_RETRIES = 5

    def __init__(self, database: ForgeDatabase, workspace: Workspace):
        super().__init__(database, workspace)
        self.prompt_engine = PromptEngine("os-gpt")
        self.chat_history = []
        self.action_history = []
        self.steps = []

    async def plan_steps(
        self, task_id: str, task_input: str, step_input: str
    ) -> List[Step]:
        step = await self.create_step(task_id=task_id, input=step_input)
        step.status = Status.running

        abilities = self.abilities.list_abilities_for_prompt()
        files = self.workspace.list(task_id, "/")
        system_prompt = self.prompt_engine.load_prompt(
            "plan-system-message", abilities=abilities, files=files
        )
        user_prompt = self.prompt_engine.load_prompt(
            "plan-user-message", input=task_input
        )
        await self.add_chat(task_id, "system", system_prompt)
        await self.add_chat(task_id, "user", user_prompt)

        final_answer, artifacts, is_last = await self.run(task_id, step)

        step = await self.db.update_step(
            task_id=task_id,
            step_id=step.step_id,
            status=Status.completed.value,
            output=final_answer,
        )
        step.artifacts = artifacts
        step.is_last = is_last
        return step

    async def complete_pending_step(
        self, task_id: str, step: Step, previous_steps: Optional[List[Step]] = None
    ) -> Step:
        step = await self.db.update_step(
            task_id=task_id,
            step_id=step.step_id,
            status=Status.running.value,
        )

        abilities = self.abilities.list_abilities_for_prompt()
        files = self.workspace.list(task_id, "/")
        system_prompt = self.prompt_engine.load_prompt(
            "complete-system-message", abilities=abilities, files=files
        )
        await self.add_chat(task_id, "system", system_prompt)

        user_prompt = self.prompt_engine.load_prompt(
            "complete-user-message",
            input=step.input,
            abilities=abilities,
            previous_steps=previous_steps,
        )
        # Replace placeholders with actual output from the specified steps
        placeholders = re.findall(r"\$\{(.+?)\}", user_prompt)
        for placeholder in placeholders:
            step_name = placeholder.split(".")[0]
            attr = placeholder.split(".")[-1]
            step = await self.get_step_by_name(task_id, step_name)
            logger.info("STEP" + str(step))
            output = getattr(step, attr, None)
            if output is not None:
                user_prompt = user_prompt.replace(
                    f"${{{placeholder}}}", json.dumps(output)
                )
            else:
                raise ValueError(f"Could not find output for step: {step_name}")

        await self.add_chat(task_id, "user", user_prompt)

        final_answer, artifacts, is_last = await self.run(task_id, step)

        step = await self.db.update_step(
            task_id=task_id,
            step_id=step.step_id,
            status=Status.completed.value,
            output=final_answer,
        )
        step.artifacts = artifacts
        step.is_last = is_last
        return step

    async def execute_step(self, task_id: str, step_request: StepRequestBody) -> Step:
        """Execute a task step and update its status and output."""
        task = await self.db.get_task(task_id)
        self.clear_chat_history()

        steps, _ = await self.db.list_steps(task_id, per_page=100)
        previous_steps, pending_steps = self._categorize_steps(steps)

        is_plan = len(pending_steps) == 0
        if is_plan:
            step = await self.plan_steps(task_id, task.input, step_request.input)
        else:
            pending_step = pending_steps[0]
            step = await self.complete_pending_step(
                task_id, pending_step, previous_steps
            )
        return step

    async def run(self, task_id: str, step: Step) -> Tuple[str, List, bool]:
        """Run the task and retrieve the output and artifacts."""
        for _ in range(self.MAX_RETRIES):
            logger.info(str(self.chat_history))
            response = await chat_completion_request(
                messages=self.chat_history, model=OPENAI_MODEL
            )
            response_message = response["choices"][0]["message"]["content"]
            logger.info(response_message)

            try:
                thoughts, action = await self._parse_output(response_message)
                observation, artifacts, is_last = await self._handle_agent_strategy(
                    task_id, step, thoughts, action
                )
                final_answer = await self._handle_agent_observation(task_id)
                return final_answer, artifacts, is_last
            except ValueError as e:
                error_message = str(e)
                logger.error(f"Error: {error_message}")
                await self.add_chat(
                    task_id,
                    "user",
                    "Reminder to always use the exact format when responding.",
                )

        logger.error("Max retries reached. Unable to parse output.")
        raise Exception("Unable to parse output after max retries.")

    def _categorize_steps(self, steps: List[Step]) -> Tuple[List[Step], List[Step]]:
        previous_steps = []
        pending_steps = []
        for step in steps:
            if step.status == Status.created:
                pending_steps.append(step)
            elif step.status == Status.completed:
                previous_steps.append(step)
        return previous_steps, pending_steps

    async def _init_chat_history(self, task_id: str, is_plan: bool):
        """Prepare initial messages for the conversation."""
        self.clear_chat_history()
        chat_history: List[ChatModel] = await self.db.get_chat_history(task_id)
        system_prompt = self._get_system_prompt(is_plan)
        await self.add_chat(task_id, "system", str(system_prompt))
        for chat in chat_history:
            if chat["role"] != "system":
                await self.add_chat(task_id, chat["role"], chat["content"])
        logger.info(str(self.chat_history))

    async def _handle_agent_strategy(
        self,
        task_id: str,
        step: Step,
        thoughts: AgentThoughts,
        action: AgentAction,
    ) -> Tuple[str, List, bool]:
        """Handle agent action, execute the function, and process the response."""
        artifacts = []
        # await self.add_chat(task_id, "assistant", thoughts.thoughts["initial_answer"])
        logger.info(
            f"Executing action '{action.action}' for task {task_id}, step {step.step_id} with arguments {action.action_args}"
        )
        await self.add_action(task_id, action.action, action.action_args)

        is_last = False
        if action.action == "ability":
            ability_name = action.action_args.get("name")
            ability_args = action.action_args.get("args")
            if ability_name == "finish":
                is_last = True
            observation = await self.abilities.run_ability(
                task_id, ability_name, **ability_args
            )
            if isinstance(observation, Artifact):
                artifacts.append(observation)
                observation = "Success\n\n" + str(observation.dict())
        elif action.action == "plan":
            planned_steps = action.action_args.get("plan")

            for step in planned_steps:
                await self.create_step(
                    task_id=task_id,
                    input=str(step["input"]) + "\n\n" + f"# Plan:\n\n{str(step)}",
                    name=step["name"],
                )
            observation = "Success!\n\n" + str(planned_steps)
        thoughts.observation = observation
        await self.add_chat(task_id, "assistant", thoughts.json(exclude_none=True))
        return observation, artifacts, is_last

    async def _handle_agent_observation(self, task_id: str) -> str:
        logger.info("Requesting final message after ability execution")
        await self.add_chat(
            task_id,
            "user",
            "Fill the final answer and Answer in the exact format based on the observation.",
        )
        second_response = await chat_completion_request(
            messages=self.chat_history, model=OPENAI_MODEL
        )
        response_message = second_response["choices"][0]["message"]["content"].strip()
        logger.info(response_message)
        thoughts, action = await self._parse_output(response_message)
        logger.info(f"Thoughts: {thoughts}")
        final_answer = thoughts.final_answer
        logger.info(f"Final message received: {final_answer}")
        await self.add_chat(task_id, "assistant", final_answer)
        return final_answer

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
        self.action_history.append(
            {
                "name": name,
                "args": args,
            }
        )
        return action

    def clear_chat_history(self):
        self.chat_history = []

    async def _parse_output(self, text: str) -> Tuple[AgentThoughts, AgentAction]:
        json_text = (
            text.replace("```", "")
            .replace(".encode()", "")
            .replace(".encode('utf-8')", "")
        )
        if json_text.startswith("json"):
            json_text = json_text[4:]

        try:
            response = json.loads(json_text.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"Could not parse JSON. error: {e}")

        thoughts = AgentThoughts(**response["thoughts"])

        is_plan = response.get("plan", None) is not None
        if is_plan:
            action = AgentAction(
                action="plan", action_args={"plan": response["plan"]}, log=text
            )
        else:
            action = AgentAction(
                action="ability", action_args=response["ability"], log=text
            )
        return thoughts, action

    async def get_step_by_name(self, task_id: str, name: str) -> Optional[Step]:
        steps, _ = await self.db.list_steps(task_id, per_page=100)
        for step in steps:
            if step.name == name:
                return step
        return None
