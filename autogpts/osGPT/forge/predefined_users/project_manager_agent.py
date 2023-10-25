import json
from typing import List, Optional, Tuple

from forge.sdk import ForgeLogger, PromptEngine

from ..agent import Agent
from ..message import SystemMessage, UserMessage
from ..schema import Activity, Issue, Project

logger = ForgeLogger(__name__)


class ProjectManagerAgent(Agent):
    ability_names: List[str] = [
        "read_file",
        "list_files",
        "change_issue_status",
        "select_worker_and_issue",
        "close_issue",
        "add_comment",
        "create_issue",
        "change_assignee",
        "finish_work",
    ]

    async def select_worker(self, project: Project) -> Tuple[Agent, Optional[Issue]]:
        """
        Selects a worker for a given project.

        Args:
            project (Project): The project for which to select a worker.

        Returns:
            tuple: A tuple containing the selected worker and the associated issue.
        """
        prompt_engine = PromptEngine("project-management")
        messages = [
            SystemMessage(
                content=prompt_engine.load_prompt(
                    "issue-tracker-system", job_title=self.job_title, project=project.display()
                )
            ),
            UserMessage(
                content=prompt_engine.load_prompt(
                    "issue-tracker-user", job_title=self.job_title, project=project.display()
                )
            ),
        ]

        max_tries = 5
        last_error = None
        for attempt in range(max_tries):
            try:
                response_message = await self.think(messages, temperature=0)
                selected_data = json.loads(response_message.content)

                try:
                    issue = project.get_issue(selected_data["issue_id"])
                except:
                    issue = None
                member = project.get_member(selected_data["next_person"])
                return member.user, issue

            except Exception as e:
                last_error = e
                logger.error(f"Error: {e}")
                messages.append(UserMessage(content="Please provide response in JSON format."))

        # If code reaches here, all attempts failed
        logger.error(f"Failed to select worker after {max_tries} attempts due to error: {str(last_error)}")
        raise ValueError("Max retries exceeded while trying to select worker.") from last_error

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
        prompt_engine = PromptEngine("project-management")
        default_prompt_engine = PromptEngine("default")
        kwargs = {"job_title": self.job_title, "issue_id": issue.id, "project": project.display()}
        messages = [
            SystemMessage(content=prompt_engine.load_prompt("resolve-issue-system", **kwargs)),
            UserMessage(content=default_prompt_engine.load_prompt("resolve-issue-user", **kwargs)),
        ]
        return await self.execute_chained_call(project, issue, messages, abilities)

    async def review_issue(
        self,
        project: Project,
        issue: Issue,
    ) -> List[Activity]:
        """Review a given issue by executing a series of predefined actions."""
        logger.info(f"Reviewing issue {issue.id} in project {project.key}")
        prompt_engine = PromptEngine("project-management")
        kwargs = {"job_title": self.job_title, "issue_id": issue.id, "project": project.display()}
        messages = [
            SystemMessage(content=prompt_engine.load_prompt("review-issue-system", **kwargs)),
            UserMessage(content=prompt_engine.load_prompt("review-issue-user", **kwargs)),
        ]
        return await self.execute_chained_call(project, issue, messages, None)
