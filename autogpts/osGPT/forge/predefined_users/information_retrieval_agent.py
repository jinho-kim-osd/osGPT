from typing import List

from forge.sdk import ForgeLogger, PromptEngine

from ..agent import Agent
from ..schema import Project, Issue, Activity
from ..message import SystemMessage, UserMessage

logger = ForgeLogger(__name__)


class InformationRetrievalAgent(Agent):
    ability_names: List[str] = [
        "read_file",
        "write_file",
        "list_files",
        "change_issue_status",
        "add_comment",
        "web_search",
        "read_webpage",
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
        # abilities = [
        #     "change_assignee",
        #     "change_issue_status",
        #     "add_comment",
        #     "finish_work",
        # ]
        prompt_engine = PromptEngine("resolve-issue")
        kwargs = {"job_title": self.job_title, "issue_id": issue.id, "project": project.display()}
        messages = [
            SystemMessage(content=prompt_engine.load_prompt("system-information-retrieval", **kwargs)),
            UserMessage(content=prompt_engine.load_prompt("user-default", **kwargs)),
        ]
        return await self.execute_chained_call(project, issue, messages, None)
