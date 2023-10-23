from typing import Optional, List, Any, Dict, Sequence

from forge.sdk import (
    Agent as AgentBase,
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
from .schema import (
    User,
    Project,
    Issue,
    UserType,
    Activity,
    Status,
)
from .db import ForgeDatabase

logger = ForgeLogger(__name__)


class Agent(User, AgentBase):
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
        logger.info(f"Resolving issue {issue.id} in project {project.key}")
        kwargs = {"job_title": self.job_title, "issue_id": issue.id, "project": project.display()}
        return await self.execute_chained_call(project, issue, "resolve-issue", None, prompt_kwargs=kwargs)

    async def review_issue(
        self,
        project: Project,
        issue: Issue,
    ) -> Dict[str, Any]:
        """Review a given issue by executing a series of predefined actions."""
        logger.info(f"Reviewing issue {issue.id} in project {project.key}")
        kwargs = {"job_title": self.job_title, "issue_id": issue.id, "project": project.display()}
        return await self.execute_chained_call(project, issue, "review-issue", None, prompt_kwargs=kwargs)

    async def think(
        self,
        messages: Sequence[Message],
        functions: Optional[Dict[str, Any]] = None,
        function_call: Optional[str] = None,
    ) -> AIMessage:
        """Process a sequence of messages and execute the given function call if provided."""
        return await invoke(messages, functions, function_call)

    async def execute_chained_call(
        self,
        project: Project,
        issue: Issue,
        prompt_name: str,
        ability_names: Optional[List[str]] = None,
        max_chained_calls: int = 10,
        prompt_kwargs: Dict[str, Any] = {},
    ) -> List[Activity]:
        """Execute a series of actions defined by the given prompt name and return the resulting activities."""
        logger.info(f"Executing chained call {prompt_name} for issue {issue.id}")
        prompt_engine = PromptEngine(prompt_name)
        messages = [
            SystemMessage(content=prompt_engine.load_prompt("system", **prompt_kwargs)),
            UserMessage(content=prompt_engine.load_prompt("user", **prompt_kwargs)),
        ]

        functions = self.abilities.list_abilities_for_function_calling(ability_names)
        return await self._process_chained_calls(project, issue, messages, functions, max_chained_calls)

    async def _process_chained_calls(
        self, project: Project, issue: Issue, messages: List[Message], functions: Dict[str, Any], max_chained_calls: int
    ) -> List[Activity]:
        """Iteratively process a series of messages and function calls, returning the accumulated activities."""
        activities = []
        stack = 0

        while stack < max_chained_calls:
            stack += 1
            print(stack, [message.to_openai_message() for message in messages])
            message = await self.think(messages, functions=functions)
            if message.function_call:
                logger.info(
                    f"Handling function call {message.function_call.name}({str(message.function_call.arguments)})"
                )
                fn_response = await self._handle_function_call(project, issue, message.function_call)
                logger.info(fn_response.summary())
                if fn_response.activities:
                    return activities + fn_response.activities

                messages.append(
                    FunctionMessage(
                        content=fn_response.message,
                        function_call=FunctionCall(
                            name=message.function_call.name, arguments=message.function_call.arguments
                        ),
                    )
                )
            elif not message.content:
                logger.info("No content in the message, breaking the loop")
                break
            else:
                logger.info(message.content)
                messages.append(message)

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
