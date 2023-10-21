from typing import Optional, Dict, Any, Tuple, List
import json
from forge.sdk import ForgeLogger, PromptEngine

from .agent_user import AgentUser
from .schema import Project, Issue, Activity
from .utils import get_openai_response

logger = ForgeLogger(__name__)


class ProjectManagerAgentUser(AgentUser):
    async def select_worker(
        self,
        project: Project,
    ) -> Tuple[AgentUser, Optional[Issue]]:
        prompt_engine = PromptEngine("select-worker")
        project_member = project.get_member(self.public_name)
        system_prompt = prompt_engine.load_prompt(
            template="system", job_title=project_member.user.job_title
        )
        user_prompt = prompt_engine.load_prompt(
            template="user",
            project=project.display(),
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
            f"[{project.key}] {self.public_name} > Next worker: {response['next_person']} (Issue ID: {response['issue_id']})"
        )
        issue = project.get_issue(response["issue_id"])
        member = project.get_member(response["next_person"])
        worker = member.user
        return worker, issue

    async def work_on_issue(self, project: Project, issue: Issue) -> List[Activity]:
        # TODO: clarify requirements?
        return await super().work_on_issue(project, issue)

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
