import json
from typing import Optional, List, Any, Dict

from forge.sdk import (
    Agent,
    ForgeLogger,
    PromptEngine,
)
from .utils import get_openai_response
from .workspace import CollaborationWorkspace

from .abilities.registry import ForgeAbilityRegister
from .schema import (
    User,
    Project,
    Issue,
    IssueLinkType,
    Comment,
    UserType,
    Activity,
    Status,
    StatusChangeActivity,
)
from .db import ForgeDatabase

logger = ForgeLogger(__name__)


class AgentUser(User, Agent):
    db: ForgeDatabase
    type: UserType = UserType.AGENT
    workspace: CollaborationWorkspace
    ability_names: Optional[List[str]]

    class Config:
        extra = "allow"

    def __str__(self):
        return f"AgentUser({self.name}, {self.role})"

    def __init__(self, **data):
        super().__init__(**data)
        self.abilities = ForgeAbilityRegister(self, self.ability_names)

    async def select_issue(self, project: Project) -> Optional[Issue]:
        for issue in project.issues:
            if issue.assignee and issue.assignee.id == self.id:
                # Status check
                if issue.status not in [
                    Status.OPEN,
                    Status.REOPENED,
                    Status.IN_PROGRESS,
                ]:
                    continue

                # Link type check
                blocked_issues = [
                    link
                    for link in issue.links
                    if link.type == IssueLinkType.IS_BLOCKED_BY
                ]
                if blocked_issues:
                    continue

                # If the issue satisfies all the conditions, return it
                return issue

        # If no appropriate issue is found
        return None

    async def work_on_issue(self, project: Project, issue: Issue) -> List[Activity]:
        old_status = issue.status
        issue.status = Status.IN_PROGRESS
        activities = [
            StatusChangeActivity(
                old_status=old_status, new_status=issue.status, created_by=self
            )
        ]
        return activities

    async def resolve_issue(self, project: Project, issue: Issue) -> List[Activity]:
        return await self.execute_task_with_prompt(
            project, issue, "resolve-issue", None
        )

    async def review_issue(
        self,
        project: Project,
        issue: Issue,
    ) -> Dict[str, Any]:
        raise NotImplementedError

    async def select_worker(
        self,
        project: Project,
    ) -> Optional["AgentUser"]:
        raise NotImplementedError

    async def execute_task_with_prompt(
        self,
        project: Project,
        issue: Issue,
        prompt_name: str,
        ability_names: Optional[List[str]] = None,
        force_function: bool = True,
        max_chained_calls: int = 2,
    ) -> List[Activity]:
        activities = []

        prompt_engine = PromptEngine(prompt_name)
        workspace_role = self.workspace.get_workspace_role_with_user_name(self.name)
        system_prompt = prompt_engine.load_prompt(
            template="system", workspace_role=workspace_role
        )

        current_workspace = self.workspace.display()
        current_issue = issue.display()
        user_prompt = prompt_engine.load_prompt(
            template="user",
            current_workspace=current_workspace,
            current_issue=current_issue,
        )
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {"role": "user", "content": user_prompt},
        ]
        functions = self.abilities.list_abilities_for_function_calling(ability_names)
        activities = await self.process_chained_calls(
            project,
            issue,
            messages,
            functions,
            force_function=force_function,
            max_chained_calls=max_chained_calls,
        )
        return activities

    async def process_chained_calls(
        self,
        project: Project,
        issue: Optional[Issue] = None,
        messages: List[Dict[str, Any]] = [],
        functions: Optional[Dict[str, Any]] = None,
        force_function: bool = False,
        max_chained_calls: int = 2,
    ) -> List[Activity]:
        activities = []

        stack = 0
        prev_message_content = None
        while stack < max_chained_calls:
            logger.info(
                f"[{project.key}-{issue.id}] > Process chained calls (stack: {stack})"
            )
            message = await get_openai_response(messages, functions=functions)

            if "function_call" in message:
                fn_name = message["function_call"]["name"]
                fn_args = json.loads(message["function_call"]["arguments"])
                logger.info(
                    f"[{project.key}-{issue.id}] > Function request: {fn_name}({fn_args})"
                )
                try:
                    fn_response = await self.abilities.run_ability(
                        project, issue, fn_name, **fn_args
                    )
                    if isinstance(fn_response, Activity):
                        fn_response_str = str(fn_response)
                        activities.append(fn_response)
                    elif isinstance(fn_response, List):
                        fn_response_str = "["
                        for item in fn_response:
                            if isinstance(item, Activity):
                                fn_response_str += str(item) + ",\n"
                                activities.append(item)
                            else:
                                fn_response_str += str(item)
                        fn_response_str += "]"
                    else:
                        fn_response_str = str(fn_response)
                except Exception as e:
                    fn_response_str = str(e)
                messages.append(
                    {
                        "role": "function",
                        "name": fn_name,
                        "content": fn_response_str,
                    }
                )

                logger.info(
                    f"[{project.key}-{issue.id}] > Function response: {fn_response_str}"
                )
            elif message["content"] in ["", prev_message_content]:
                break
            else:
                if force_function:
                    logger.info(f"[{project.key}-{issue.id}] > Invalid Response.")
                    messages.append({"role": "user", "content": "Use functions only."})
                else:
                    comment = Comment(content=message["content"], created_by=self)
                    logger.info(f"[{project.key}-{issue.id}] > {comment}")
                    issue.add_activity(comment)
                    messages.append({"role": "user", "content": project.display()})
                    activities.append(comment)
                    prev_message_content = message["content"]

            # Add workspace landscape for observation
            messages.append({"role": "user", "content": project.display()})
            stack += 1

        if stack >= max_chained_calls:
            logger.error(
                f"[{project.key}-{issue.id}] > Reached max chained function calls: {max_chained_calls}"
            )

        return activities
