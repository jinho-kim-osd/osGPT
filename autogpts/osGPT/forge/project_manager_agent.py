from typing import Optional, List, Dict, Any

from forge.sdk import ForgeLogger, PromptEngine

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
    async def resolve_issue(
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

    async def review_issue(
        self,
        project: Project,
        issue: Optional[Issue] = None,
    ) -> Dict[str, Any]:
        return await self.execute_task_with_prompt(
            project,
            issue,
            "review-issue",
            [
                "create_issue",
                "change_assinee",
                "change_issue_status",
                "read_file",
                "list_files",
                "add_comment",
            ],
        )

    async def select_worker(
        self,
        project: Project,
    ) -> Optional[AgentUser]:
        prompt_engine = PromptEngine("select-worker")
        system_prompt = prompt_engine.load_prompt(template="system")
        user_prompt = prompt_engine.load_prompt(
            template="user",
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
