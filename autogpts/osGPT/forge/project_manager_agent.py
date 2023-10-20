from typing import Optional, Dict, Any, Tuple, List
import json
from forge.sdk import ForgeLogger, PromptEngine

from .agent_user import AgentUser
from .schema import Project, Issue, User, Activity
from .utils import get_openai_response

logger = ForgeLogger(__name__)


class ProjectManagerAgentUser(AgentUser):
    async def select_worker(
        self,
        project: Project,
    ) -> Tuple[User, Optional[Issue]]:
        prompt_engine = PromptEngine("select-worker")
        project_member = project.get_member(self.id)
        system_prompt = prompt_engine.load_prompt(
            template="system", project_role=project_member.project_role
        )
        user_prompt = prompt_engine.load_prompt(
            template="user",
            current_project=project.display(),
        )
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {"role": "user", "content": user_prompt},
        ]
        message = await get_openai_response(messages)
        response = json.loads(message["content"])
        logger.info(
            f"[{project.key}] {self.name} > Next speaker is {response['next_person']}(Issue ID: {response['issue_id']})"
        )
        issue = project.get_issue(response["issue_id"])
        worker = project.get_user_with_name(response["next_person"])
        return worker, issue

    async def resolve_issue(self, project: Project, issue: Issue) -> List[Activity]:
        return await self.execute_task_with_prompt(
            project,
            issue,
            "resolve-issue-action",
            [
                "change_assignee",
                "change_issue_status",
                "read_file",
                "add_comment",
                "finish_work",
            ],
        )

    async def review_issue(
        self,
        project: Project,
        issue: Issue,
    ) -> Dict[str, Any]:
        return await self.execute_task_with_prompt(
            project,
            issue,
            "review-issue",
            [
                "change_assignee",
                "change_issue_status",
                "close_issue",
                "read_file",
                "list_files",
                "add_comment",
            ],
        )

    async def decide_reopen(
        self,
        project: Project,
        issue: Issue,
    ) -> Dict[str, Any]:
        raise NotImplementedError
