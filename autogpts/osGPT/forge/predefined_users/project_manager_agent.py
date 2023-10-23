import json
from typing import List, Optional, Tuple

from forge.sdk import ForgeLogger, PromptEngine

from ..agent_user import AgentUser
from ..message import SystemMessage, UserMessage
from ..schema import Activity, Issue, Project

logger = ForgeLogger(__name__)


class ProjectManagerAgentUser(AgentUser):
    async def select_worker(self, project: Project) -> Tuple[AgentUser, Optional[Issue]]:
        """
        Selects a worker for a given project.

        Args:
            project (Project): The project for which to select a worker.

        Returns:
            tuple: A tuple containing the selected worker and the associated issue.
        """
        prompt_engine = PromptEngine("select-worker")
        messages = [
            SystemMessage(
                content=prompt_engine.load_prompt("system", job_title=self.job_title, project=project.display())
            ),
            UserMessage(content=prompt_engine.load_prompt("user", job_title=self.job_title, project=project.display())),
        ]

        response_message = await self.think(messages)
        selected_data = json.loads(response_message.content)

        issue = project.get_issue(selected_data["issue_id"])
        member = project.get_member(selected_data["next_person"])

        return member.user, issue

    async def resolve_issue(self, project: Project, issue: Issue) -> List[Activity]:
        """
        Resolves an issue within a project.

        Args:
            project (Project): The project containing the issue.
            issue (Issue): The issue to resolve.

        Returns:
            list: A list of activities performed while resolving the issue.
        """
        logger.info(f"Resolving issue {issue.id} in project {project.key}")
        abilities = [
            "change_assignee",
            "change_issue_status",
            "add_comment",
            "finish_work",
        ]
        kwargs = {"job_title": self.job_title, "issue_id": issue.id, "project": project.display()}
        return await self.execute_chained_call(
            project, issue, "resolve-issue-project-manager", abilities, prompt_kwargs=kwargs
        )

    async def review_issue(self, project: Project, issue: Issue) -> List[Activity]:
        """
        Reviews an issue within a project.

        Args:
            project (Project): The project containing the issue.
            issue (Issue): The issue to review.

        Returns:
            list: A list of activities performed while reviewing the issue.
        """
        logger.info(f"Reviewing issue {issue.id} in project {project.key}")
        abilities = [
            "change_assignee",
            "change_issue_status",
            "close_issue",
            "read_file",
            "list_files",
            "add_comment",
        ]
        kwargs = {"job_title": self.job_title, "issue_id": issue.id, "project": project.display()}
        return await self.execute_chained_call(project, issue, "review-issue", abilities, prompt_kwargs=kwargs)
