import json
from typing import Optional, List, Any, Dict

from forge.sdk import (
    Agent,
    ForgeLogger,
    PromptEngine,
)
from .utils import get_openai_response
from .workspace import CollaborationWorkspace

from .abilities.schema import AbilityResult
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
        logger.error(f"[{project.key}-{issue.id}] > Work on Issue")
        old_status = issue.status
        issue.status = Status.IN_PROGRESS

        activity = StatusChangeActivity(
            old_status=old_status, new_status=issue.status, created_by=self
        )
        issue.add_activity(activity)

        activities = [activity]
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
        max_chained_calls: int = 1,
    ) -> List[Activity]:
        activities = []

        prompt_engine = PromptEngine(prompt_name)
        project_member = project.get_member(self.id)
        system_prompt = prompt_engine.load_prompt(
            template="system", project_role=project_member.project_role
        )

        user_prompt = prompt_engine.load_prompt(
            template="user",
            project=project.display(),
            issue_id=issue.id,
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
        max_chained_calls: int = 3,
    ) -> List[Activity]:
        activities = []
        is_activity_type = False
        stack = 0

        if force_function:
            messages.append({"role": "user", "content": "Use functions only."})

        while not is_activity_type and stack < max_chained_calls:
            logger.info(f"[{project.key}-{issue.id}] > Stack: {stack}")
            message = await get_openai_response(messages, functions=functions)
            if "function_call" in message:
                fn_name = message["function_call"]["name"]
                fn_args = json.loads(message["function_call"]["arguments"])
                logger.info(
                    f"[{project.key}-{issue.id}] > Function request: {fn_name}({fn_args})"
                )
                try:
                    fn_response: AbilityResult = await self.abilities.run_ability(
                        project, issue, fn_name, **fn_args
                    )
                    if isinstance(fn_response, str):
                        logger.error(
                            f"[{project.key}-{issue.id}] > Function Response: {fn_response}"
                        )
                    logger.info(str(fn_response.summary()))

                    for activity in fn_response.activities:
                        activities.append(activity)
                        is_activity_type = True

                    if is_activity_type:
                        break

                except Exception as e:
                    logger.error(f"[{project.key}-{issue.id}] > Error: {str(e)}")
                    fn_response = AbilityResult(
                        ability_name=fn_name,
                        ability_args=fn_args,
                        message=str(e),
                        success=False,
                    )

                messages.append(
                    {
                        "role": "function",
                        "name": fn_name,
                        "content": fn_response.summary(),
                    }
                )
            elif message["content"] == "":
                break
            else:
                if force_function:
                    logger.error(
                        f"[{project.key}-{issue.id}] > Invalid Response: {str(message)}"
                    )
                    messages.append({"role": "user", "content": "Use functions only."})
                else:
                    raise NotImplementedError
            print(project.display())
            messages.append({"role": "user", "content": project.display()})

        if stack >= max_chained_calls:
            logger.info(
                f"[{project.key}-{issue.id}] > Reached max chained function calls: {max_chained_calls}"
            )
        return activities
