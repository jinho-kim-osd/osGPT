import os
from typing import Optional, List
from forge.sdk import (
    Agent,
    Step,
    StepRequestBody,
    ForgeLogger,
    Status as StepStatus,
    Task,
    TaskRequestBody,
)
from forge.sdk.abilities.registry import AbilityRegister
from .schema import (
    Status,
    Project,
    IssueType,
    Comment,
    Activity,
    Attachment,
    AttachmentUploadActivity,
)
from .predefined_users.project_manager_agent import ProjectManagerAgent
from .db import ForgeDatabase
from .workspace import Workspace


logger = ForgeLogger(__name__)


class JiraAgent(Agent):
    """Agent emulating Jira or similar project management systems."""

    def __init__(
        self,
        database: ForgeDatabase,
        workspace: Workspace,
    ):
        self.db = database
        self.workspace: Workspace = workspace
        self.abilities = AbilityRegister(self, None)

    def reset(self):
        """Clear all issues in each project within the workspace."""
        for project in self.workspace.projects:
            project.issues = []

    async def create_task(self, task_request: TaskRequestBody) -> Task:
        """Create a task and reset the workspace."""
        self.reset()
        return await super().create_task(task_request)

    def get_current_project(self) -> Project:
        """Retrieve the current project if there's only one project in the workspace."""
        if len(self.workspace.projects) == 1:
            return self.workspace.projects[0]
        raise LookupError("Multiple projects found")

    def create_issue_from_user_request(self, task_id: str, project: Project, input: str):
        """Create and add an issue to the project from a given input."""
        self.workspace.register_project_key_path(project.key, f"./{task_id}")
        user_proxy = project.project_leader
        issue = project.create_issue(
            type=IssueType.TASK,
            summary=input,
            reporter=user_proxy,
            assignee=user_proxy,
        )

        # NOTE: Originally added to address a LabelCsv issue, but has been deprecated due to updates in the benchmark.
        # comment = Comment(
        #     created_by=user_proxy,
        #     content="Strictly adhere to letter case in the assigned tasks; remember that 'Yellow' and 'yellow' are NOT the same.",
        # )
        # issue.add_activity(comment)

        file_infos = self.workspace.list_files_by_key(project.key)
        for file_info in file_infos:
            attachment = Attachment(
                url=file_info.relative_url,
                filename=file_info.filename,
                filesize=file_info.filesize,
            )
            issue.add_attachment(attachment, user_proxy)

    async def execute_step(self, task_id: str, step_request: StepRequestBody) -> Step:
        """Execute the task step, update its status and output."""
        step = await self.next_step(task_id) or await self.db.create_step(task_id=task_id, input=step_request)
        await self.db.update_step(task_id, step.step_id, "running")

        project = (
            self.get_current_project()
            if not step_request.additional_input
            else self.workspace.get_project(step_request.additional_input.get("project_key"))
        )

        if step_request.input:
            self.create_issue_from_user_request(task_id, project, step_request.input)

        step_activities = await self.process_issues(project)

        for activity in step_activities:
            await self.handle_activity(task_id, step, activity)

        unclosed_issues = [issue for issue in project.issues if issue.status != Status.CLOSED]
        await self.db.update_step(task_id, step.step_id, "completed", output=project.display())
        step.is_last = len(unclosed_issues) == 0
        return step

    async def process_issues(self, project: Project) -> List[Activity]:
        """
        Process issues in the project and return a list of activities.
        Each issue in the project that is not closed will be processed according to its status.
        The project leader selects a worker to perform actions on the issue.

        Parameters:
            project (Project): The project containing the issues to be processed.

        Returns:
            List[Activity]: A list of activities resulting from processing the issues.
        """
        logger.info(f"Starting to process issues for project {project.key}")

        # Getting the project leader who is an instance of ProjectManagerAgent
        project_leader: ProjectManagerAgent = project.project_leader

        # Project leader selects a worker for the issue
        worker, issue = await project_leader.select_worker(project)
        logger.info(f"Worker {worker.public_name} selected for issue {issue.id} in project {project.key}")

        # Displaying the current state of the project
        logger.info(f"Current state of project {project.key}:\n{project.display()}")

        activities = []
        # Processing the issue based on its current status
        if issue.status in [Status.OPEN, Status.REOPENED]:
            logger.info(f"Issue {issue.id} is OPEN or REOPENED. Worker {worker.public_name} is starting work on it.")
            activities = await worker.work_on_issue(project, issue)

        elif issue.status == Status.IN_PROGRESS:
            logger.info(f"Issue {issue.id} is IN PROGRESS. Worker {worker.public_name} is resolving it.")
            activities = await worker.resolve_issue(project, issue)

        elif issue.status == Status.RESOLVED:
            logger.info(f"Issue {issue.id} is RESOLVED. Worker {worker.public_name} is reviewing it.")
            activities = await worker.review_issue(project, issue)

        else:
            logger.warning(f"Issue {issue.id} has an unexpected status {issue.status}.")

        # Displaying the updated state of the project after processing the issue
        logger.info(f"Updated state of project {project.key} after processing issue {issue.id}:\n{project.display()}")

        return activities

    async def handle_activity(self, task_id: str, step: Step, activity: Activity):
        """Handle activity, create artifact if it's an attachment or comment with attachments."""
        if isinstance(activity, (AttachmentUploadActivity, Comment)) and activity.attachments:
            for attachment in activity.attachments:
                await self.db.create_artifact(
                    task_id, attachment.filename, attachment.url, agent_created=True, step_id=step.step_id
                )

    async def next_step(self, task_id: str) -> Optional[Step]:
        """Retrieve the next step to be executed, if any."""
        steps, _ = await self.db.list_steps(task_id, per_page=int(os.environ.get("MAX_STEPS_PER_PAGE", 1000)))
        return next((s for s in steps if s.status == StepStatus.created), None)
