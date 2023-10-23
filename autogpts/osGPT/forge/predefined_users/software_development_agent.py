from typing import List, Optional

from forge.sdk import ForgeLogger

from ..agent import Agent
from ..schema import UserType, Project, Issue, Activity, Comment

logger = ForgeLogger(__name__)


class SoftwareDevelopmentAgent(Agent):
    ability_names: List[str] = [
        "change_issue_status",
        "add_comment",
        "read_file",
        "write_file",
        "list_files",
        "design_system_architecture",
        "read_system_architecture",
        # "write_code",
        "finish_work",
    ]

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
