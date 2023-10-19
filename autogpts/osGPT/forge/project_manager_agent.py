from typing import Optional, List, Dict, Any

from forge.sdk import ForgeLogger

from .agent_user import AgentUser, TERMINATION_WORD
from .schema import (
    Project,
    Issue,
    Status,
    IssueType,
    Comment,
    Activity,
)
from .utils import get_openai_response

logger = ForgeLogger(__name__)


class ProjectManagerAgentUser(AgentUser):
    async def resolve_issues(
        self, project: Project, issue: Optional[Issue] = None
    ) -> List[Activity]:
        activities = []
        if issue is None or issue.status in [
            Status.IN_PROGRESS,
            Status.RESOLVED,
            Status.CLOSED,
        ]:
            management_activities = await self.manage_workspace(project, issue)
            activities.extend(management_activities)
        elif issue.status in [Status.OPEN, Status.REOPENED]:
            plan_activities = await self.create_project_plan(project, issue)
            activities.extend(plan_activities)
        else:
            logger.info(str(issue))
            raise NotImplementedError
        return activities

    async def clarify_requirements(
        self,
        requirements: str,
        project: Project,
        issue: Optional[Issue] = None,
    ) -> List[Activity]:
        activities = []
        logger.info(
            f"[{project.key}-{issue.id if issue else 'No Issue'}] {self.name} > Clarifying requirements for the project"
        )
        system_prompt = self.build_system_prompt(template="clarify-requirements-system")
        user_prompt = self.build_system_prompt(
            template="clarify-requirements-user",
            requirements=requirements,
            current_workspace_structure=self.workspace.display(),
        )
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {"role": "user", "content": user_prompt},
        ]
        functions = self.abilities.list_abilities_for_function_calling()
        activities = await self.process_chained_calls(
            project,
            issue,
            messages,
            functions,
            force_function=False,
            max_chained_calls=2,
        )
        return activities

    async def create_project_plan(
        self,
        project: Project,
        issue: Optional[Issue] = None,
    ) -> Dict[str, Any]:
        logger.info(
            f"[{project.key}-{issue.id if issue else 'No Issue'}] {self.name} > Create a project plan"
        )

        system_prompt = self.build_system_prompt(template="plan-project-system")
        user_prompt = self.build_system_prompt(
            template="plan-project-user",
            current_workspace_structure=self.workspace.display(),
        )

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {"role": "user", "content": user_prompt},
        ]
        functions = self.abilities.list_abilities_for_function_calling(
            [
                "create_issue",
                "change_assinee",
                "change_issue_status",
                "read_file",
                "list_files",
                "add_comment",
            ]
        )
        activities = await self.process_chained_calls(
            project,
            issue,
            messages,
            functions,
            force_function=False,
            max_chained_calls=2,
        )
        return activities

    async def select_next_speaker(
        self,
        project: Project,
    ) -> Optional[AgentUser]:
        logger.info(f"[{project.key}] {self.name} > Selecting a next speaker")
        system_prompt = self.build_system_prompt(template="select-next-speaker-system")
        user_prompt = self.build_system_prompt(
            template="select-next-speaker-user",
            current_workspace_structure=self.workspace.display(),
        )
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {"role": "user", "content": user_prompt},
        ]
        message = await get_openai_response(messages)
        logger.info(
            f"[{project.key}] {self.name} > Next speaker is {message['content']}"
        )
        if message["content"] == TERMINATION_WORD:
            return None
        speaker = self.workspace.get_user_with_name(message["content"])
        return speaker

    async def manage_workspace(
        self,
        project: Project,
        issue: Optional[Issue] = None,
    ) -> List[Activity]:
        activities = []
        logger.info(
            f"[{project.key}-{issue.id if issue else 'No Issue'}] {self.name} > Managing a workspace"
        )
        system_prompt = self.build_system_prompt(template="manage-workspace-system")
        user_prompt = self.build_system_prompt(
            template="manage-workspace-user",
            current_workspace_structure=self.workspace.display(),
        )
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {"role": "user", "content": user_prompt},
        ]
        functions = self.abilities.list_abilities_for_function_calling()
        activities = await self.process_chained_calls(
            project,
            issue,
            messages,
            functions,
            force_function=False,
            max_chained_calls=2,
        )
        return activities
