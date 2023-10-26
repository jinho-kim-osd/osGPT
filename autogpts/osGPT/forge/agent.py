from typing import Optional, List, Any, Dict, Sequence, Literal

from forge.sdk import (
    # Agent as AgentBase,
    ForgeLogger,
    PromptEngine,
)
from .message import (
    Message,
    SystemMessage,
    UserMessage,
    AIMessage,
    FunctionMessage,
    FunctionCall,
)
from .utils import invoke
from .workspace import Workspace
from .abilities.schema import AbilityResult
from .abilities.registry import ForgeAbilityRegister
from .schema import User, Project, Issue, UserType, Activity, Status, Comment
from .db import ForgeDatabase

logger = ForgeLogger(__name__)


class Agent(User):
    """
    A user type that acts both as a user and an agent, equipped with abilities and behaviors
    to interact with and modify the workspace and its contents.
    """

    db: ForgeDatabase
    type: UserType = UserType.AGENT
    workspace: Workspace
    ability_names: Optional[List[str]]

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"

    def __init__(self, **data):
        super().__init__(**data)
        self.abilities = ForgeAbilityRegister(self, self.ability_names)

    async def work_on_issue(self, project: Project, issue: Issue) -> List[Activity]:
        """Start working on a given issue and change its status to IN_PROGRESS."""
        logger.info(f"Working on issue {issue.id} in project {project.key}")
        issue.change_status(Status.IN_PROGRESS, self)
        return [issue.get_last_activity()]

    async def resolve_issue(self, project: Project, issue: Issue) -> List[Activity]:
        """Resolve a given issue by executing a series of predefined actions."""
        logger.info(f"Reviewing issue {issue.id} in project {project.key}")
        prompt_engine = PromptEngine("default")
        kwargs = {"job_title": self.job_title, "issue_id": issue.id, "project": project.display()}
        messages = [
            SystemMessage(content=prompt_engine.load_prompt("resolve-issue-system", **kwargs)),
            UserMessage(content=prompt_engine.load_prompt("resolve-issue-user", **kwargs)),
        ]
        return await self.execute_chained_call(project, issue, messages, None)

    async def review_issue(
        self,
        project: Project,
        issue: Issue,
    ) -> Dict[str, Any]:
        """Review a given issue by executing a series of predefined actions."""
        raise NotImplementedError

    async def think(
        self,
        messages: Sequence[Message],
        functions: Optional[Dict[str, Any]] = None,
        function_call: Optional[str] = None,
        temperature: float = 0.3,
        top_p: float = 0.2,
    ) -> AIMessage:
        """Process a sequence of messages and execute the given function call if provided."""
        return await invoke(messages, functions, function_call, temperature=temperature, top_p=top_p)

    async def execute_chained_call(
        self,
        project: Project,
        issue: Issue,
        messages: List[Message],
        ability_names: Optional[List[str]] = None,
        max_chained_calls: int = 20,
    ) -> List[Activity]:
        """Execute a series of actions defined by the given prompt name and return the resulting activities."""
        logger.info(f"Executing chained call for issue {issue.id}")
        functions = self.abilities.list_abilities_for_function_calling(ability_names)
        return await self._process_chained_calls(project, issue, messages, functions, max_chained_calls)

    async def _process_chained_calls(
        self,
        project: Project,
        issue: Issue,
        messages: List[Message],
        functions: Dict[str, Any],
        max_chained_calls: int,
        stopping_method: Literal["comment", "activity"] = "comment",
    ) -> List[Activity]:
        """Iteratively process a series of messages and function calls, returning the accumulated activities."""
        activities = []
        stack = 0

        while stack < max_chained_calls:
            stack += 1
            state = project.display()
            logger.info(f"Current Stack: {stack}")
            try:
                message = await self.think(messages, functions=functions)
            except Exception as e:
                logger.error(f"Error executing think - {type(e).__name__}: {str(e)}")
                break

            if message.function_call:
                logger.info(
                    f"Handling function call {message.function_call.name}({str(message.function_call.arguments)})"
                )
                fn_response = await self._handle_function_call(project, issue, message.function_call)
                logger.info(fn_response.summary())

                if fn_response.activities:
                    if stopping_method == "activity":
                        return activities + fn_response.activities

                    if stopping_method == "comment" and any(
                        isinstance(activity, Comment) for activity in fn_response.activities
                    ):
                        return activities + fn_response.activities

                suffix = f"\n\nCurrent state of the project:\n{project.display()}" if state != project.display() else ""
                messages.append(
                    FunctionMessage(
                        content=f"Function Response:\n{fn_response.summary()}" + suffix,
                        function_call=FunctionCall(
                            name=message.function_call.name, arguments=message.function_call.arguments
                        ),
                    )
                )

                if stopping_method == "comment" and fn_response.activities:
                    activities.extend(fn_response.activities)

            elif not message.content:
                logger.info("No content in the message, breaking the loop")
                break
            else:
                logger.info(message.content)
                messages.append(message)
                messages.append(UserMessage(content=project.display()))
                messages.append(
                    UserMessage(
                        content="If you want to speak, use the 'comment' function. For all other actions, use the appropriate functions!"
                    )
                )

        return activities

    async def _handle_function_call(self, project: Project, issue: Issue, function_call: FunctionCall) -> AbilityResult:
        """Handle a function call, execute the corresponding ability, and return the result."""
        try:
            logger.info(f"Executing ability {function_call.name} for issue {issue.id}")
            return await self.abilities.run_ability(project, issue, function_call.name, **function_call.arguments)
        except Exception as e:
            logger.error(f"Error executing ability - {type(e).__name__}: {str(e)}")
            return AbilityResult(
                ability_name=function_call.name,
                ability_args=function_call.arguments,
                message=f"Error - {type(e).__name__}: {str(e)}",
                success=False,
            )
