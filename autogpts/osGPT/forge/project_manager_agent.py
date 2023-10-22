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
        thought = await self.think("select-worker", system_prompt_params={
            "job_title": self.job_title, 
        }, user_prompt_params={"project": project.display()})
        response = json.loads(thought)
        logger.info(
            f"[{project.key}] {self.public_name} > Next worker: {response['next_person']} (Issue ID: {response['issue_id']})"
        )
        issue = project.get_issue(response["issue_id"])
        member = project.get_member(response["next_person"])
        worker = member.user
        return worker, issue

    async def resolve_issue(self, project: Project, issue: Issue) -> List[Activity]:
        return await self.execute_task_with_prompt(
            project,
            issue,
            "resolve-issue-project-manager",
            [
                "change_assignee",
                "change_issue_status",
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
            # force_function=True,
        )
