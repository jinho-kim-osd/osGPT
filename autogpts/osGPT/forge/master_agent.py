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
from .user_proxy_agent import UserProxyAgent
from .slave_agent import SlaveAgent
from .agent_base import ForgeAgentBase
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


class MasterAgent(ForgeAgentBase):
    def __init__(
        self,
        database: ForgeDatabase,
        workspace: Workspace,
        name: str = "master",
        ability_names: Optional[List[str]] = None,
        system_message: str | None = None,
        use_prompt_engine: bool = True,
    ):
        super().__init__(
            database, workspace, name, ability_names, system_message, use_prompt_engine
        )
        self.agents: List[ForgeAgentBase] = [
            UserProxyAgent(
                database,
                workspace,
                name="user",
                ability_names=["finish"],
            ),
            # SlaveAgent(
            #     database,
            #     workspace,
            #     name="researcher",
            #     ability_names=["web_search", "read_webpage"],
            # ),
            SlaveAgent(
                database,
                workspace,
                name="planner",
            ),
            SlaveAgent(
                database,
                workspace,
                name="engineer",
            ),
            SlaveAgent(
                database,
                workspace,
                name="executor",
                ability_names=["run_python_code"],
            ),
        ]

    @property
    def agent_names(self) -> List[str]:
        return [agent.name for agent in self.agents]

    def agent_by_name(self, name: str) -> ForgeAgentBase:
        return self.agents[self.agent_names.index(name)]

    def next_agent(self, agent: Agent) -> ForgeAgentBase:
        return self.agents[(self.agent_names.index(agent.name) + 1) % len(self.agents)]

    async def select_speaker(
        self,
        task: Task,
        step: Step,
        last_speaker: ForgeAgentBase,
    ) -> ForgeAgentBase:
        """Select the next speaker."""
        select_speaker_prompt = self.prompt_engine.load_prompt(
            "select-speaker", agents=self.agents, agent_names=self.agent_names
        )
        await self.update_system_message(select_speaker_prompt)

        select_speaker_suffix_prompt = self.prompt_engine.load_prompt(
            "select-speaker-suffix", agents=self.agents, agent_names=self.agent_names
        )
        await self.chat_completion_request(
            self.chat_messages[self.name]
            + [
                {
                    "role": "system",
                    "name": self.name,
                    "content": select_speaker_suffix_prompt,
                }
            ],
        )
        agent_name = await self.reply_message(task.task_id, step.step_id, sender=self)
        # try:
        return self.agent_by_name(agent_name)
        # except ValueError:
        #     return self.next_agent(last_speaker)

    # async def _create_planning_step(self, task: Task) -> Step:
    #     self.reset()
    #     step = await self.create_step(
    #         task_id=task.task_id, name="planning_step", input=task.input
    #     )
    #     step.status = Status.running

    #     abilities = self.abilities.list_abilities_for_prompt()
    #     logger.info(str(abilities))
    #     files = self.workspace.list(task.task_id, "/")

    #     agent_description = ""
    #     for i, agent in enumerate(self._agents):
    #         agent_description += f"Agent {i+1} - Name: [{agent.name}]"
    #         agent_abilities = agent.abilities.list_abilities_for_prompt()
    #         agent_description += (
    #             "Use only the provided functions to plan the task execution:\n"
    #         )
    #         # for ability in agent_abilities:
    #         # agent_description +=

    #     system_prompt = self.prompt_engine.load_prompt(
    #         "plan-system-message", abilities=abilities, files=files, agents=self._agents
    #     )
    #     user_prompt = self.prompt_engine.load_prompt(
    #         "plan-user-message", input=task.input
    #     )
    #     await self.add_chat(task.task_id, "system", system_prompt)
    #     await self.add_chat(task.task_id, "user", user_prompt)
    #     return step

    # async def _create_planned_steps(
    #     self, task: Task, step: Step, planned_steps: List[Dict[str, Any]]
    # ) -> str:
    #     for planned_step in planned_steps:
    #         await self.create_step(
    #             task_id=task.task_id,
    #             input=planned_step["input"]
    #             + "\n\n"
    #             + f"# Original Plan:\n\n{str(planned_step)}",
    #             name=planned_step["name"],
    #         )
    #     observation = json.dumps(planned_steps, indent=2)
    #     return observation

    # async def _answer(
    #     self, task: Task, step: Step, observation: Optional[str] = None
    # ) -> Dict[str, Any]:
    #     last_assistant_message = next(
    #         (
    #             msg["content"]
    #             for msg in reversed(self.chat_history)
    #             if msg["role"] == "assistant"
    #         ),
    #         None,
    #     )
    #     previous_parsed_output = extract_top_level_json(last_assistant_message)
    #     previous_parsed_output["thoughts"]["observation"] = observation
    #     await self.add_chat(task.task_id, "assistant", str(previous_parsed_output))
    #     await self.add_chat(
    #         task.task_id,
    #         "user",
    #         "Fill the final answer in the exact format based on the observation. If the observation is webpage results, return it directly",
    #     )

    #     parsed_output = await self._request_chat(task, step)
    #     parsed_output["thoughts"]["observation"] = observation
    #     output = json.dumps(parsed_output, indent=2)
    #     logger.info(f"Final message received: {output}")
    #     await self.add_chat(task.task_id, "assistant", output)

    #     step = await self.db.update_step(
    #         task_id=task.task_id,
    #         step_id=step.step_id,
    #         status=Status.completed.value,
    #         output=output,
    #     )

    #     is_plan = previous_parsed_output.get("plan", False) is not False
    #     if is_plan:
    #         self.clear_chat_history()
    #     is_finished = (
    #         previous_parsed_output.get("ability", {}).get("name", None) == "finish"
    #     )
    #     step.is_last = is_finished
    #     return step

    # async def _handle_action(self, action: Action, step: Optional[Step] = None) -> Any:
    #     logger.info("Action: " + str(action.name))
    #     if isinstance(action, PlanStepsAction):
    #         step = await self._create_planning_step(action.task)
    #         step_or_action = RequestChatAction(action.task, step)
    #         while isinstance(step_or_action, Action):
    #             step_or_action = await self._handle_action(step_or_action, step)
    #         step = step_or_action
    #         return step
    #     elif isinstance(action, ExecuteStepAction):
    #         step = await self._initialize_step(action.task, action.step)
    #         step_or_action = RequestChatAction(action.task, step)
    #         while isinstance(step_or_action, Action):
    #             step_or_action = await self._handle_action(step_or_action, step)
    #         step = step_or_action
    #         return step
    #     elif isinstance(action, RequestChatAction):
    #         parsed_output = await self._request_chat(action.task, action.step)
    #         if parsed_output.get("plan", None):
    #             planned_steps = parsed_output["plan"]
    #             return CreatePlannedStepsAction(action.task, step, planned_steps)
    #         elif parsed_output.get("ability", None):
    #             ability = parsed_output["ability"]
    #             return RunAbilityAction(action.task, step, ability)
    #         else:
    #             raise NotImplementedError
    #             # return AnswerAction(action.task, step)
    #     elif isinstance(action, CreatePlannedStepsAction):
    #         observation = await self._create_planned_steps(
    #             action.task, action.step, action.planned_steps
    #         )
    #         return AnswerAction(action.task, action.step, observation)
    #     elif isinstance(action, RunAbilityAction):
    #         observation = await self._run_ability(
    #             action.task, action.step, action.ability
    #         )
    #         return AnswerAction(action.task, action.step, observation)
    #     # elif isinstance(action, EvaluateAction):
    #     #     observation = await self._run_ability(action)
    #     #     return step
    #     # elif isinstance(action, GenerateReflectionAction):
    #     #     observation = await self._run_ability(action)
    #     #     return step
    #     elif isinstance(action, AnswerAction):
    #         step = await self._answer(action.task, action.step, action.observation)
    #         return step
    #     else:
    #         raise NotImplementedError

    async def next_step(self, task_id: str) -> Optional[Step]:
        steps, _ = await self.db.list_steps(task_id, per_page=100)
        _, pending_steps = self._categorize_steps(steps)
        if pending_steps:
            return pending_steps.pop(0)
        return None

    async def execute_step(self, task_id: str, step_request: StepRequestBody) -> Step:
        """Execute a task step and update its status and output."""
        task = await self.db.get_task(task_id)
        step = await self.next_step(task_id)

        logger.info("Next Step : " + str(step))
        # Create a initial Step
        if step is None:
            assignee = "user"
            message = {"role": "user", "name": assignee, "content": task.input}
            step = await self.create_step(
                task_id,
                task.input,
                "plan_steps",
                additional_input={"sender": assignee, "recipient": None},
            )
        else:
            agent_name = await self.select_speaker(task, step, last_speaker=assignee)
            assignee = self.agent_by_name(agent_name)
            # message = step.input
            message = await self.get_last_message(self)
            logger.info("Last Message :" + str(message))

        # while True:
        if message:
            self.chat_messages[self.name].append(message)
            # broadcast the message to all agents except the speaker
            for agent in self.agents:
                if agent != assignee:
                    await self.send_message(
                        task_id,
                        message["content"],
                        agent,
                        step.step_id,
                        request_reply=False,
                    )

        agent_name = await self.select_speaker(task, step, last_speaker=assignee)
        assignee = self.agent_by_name(agent_name)
        logger.info("Next Assignee :" + str(assignee.name))

        reply = await assignee.reply_message(task_id, step.step_id, sender=self)
        logger.info("Reply :" + str(reply))

        # # The assignee sends the message without requesting a reply
        # await assignee.send_message(task_id, reply, self, request_reply=False)
        # message = await self.get_last_message(assignee)

        # logger.info("Last Message :" + str(message))

        # step = await self.next_step(task_id)
        # if step is None:
        #     break

        # if len(pending_steps) == 0:
        #     agent = self.agent_by_name("user")
        #     agent.add_chat(task.task_id, "user", task.input)
        # else:
        #     agent = await self.select_speaker(task, last_speaker=self)
        # is_plan = len(pending_steps) == 0
        # if is_plan:
        #     action = PlanStepsAction(task)
        # else:
        #     # TODO: human-editing using step_request
        #     step = pending_steps[0]
        #     logger.info("Execute Step!: " + str(step.dict()))
        #     action = ExecuteStepAction(task, step)

        # step: Step = await self._handle_action(action)
        return step
