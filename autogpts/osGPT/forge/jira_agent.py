import os
from typing import Optional
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
    User,
    Status,
    Project,
    Epic,
    Issue,
    IssueType,
    IssueLinkType,
    Comment,
    Attachment,
    AttachmentUploadActivity,
    IssueCreationActivity,
)
from .project_manager_agent import ProjectManagerAgentUser
from .db import ForgeDatabase
from .workspace import Workspace


logger = ForgeLogger(__name__)


class JiraAgent(Agent):
    """
    An agent designed to emulate Jira or other project management systems, capable of being
    replaced by or integrated with actual systems for real-world application and use.
    """

    def __init__(
        self,
        database: ForgeDatabase,
        workspace: Workspace,
    ):
        self.db = database
        self.workspace: Workspace = workspace
        self.abilities = AbilityRegister(self, None)

    def reset(self):
        # Remove all issues
        for project in self.workspace.projects:
            project.issues = []

    async def create_task(self, task_request: TaskRequestBody) -> Task:
        self.reset()
        task = await super().create_task(task_request)
        return task

    def create_issue(
        self,
        reporter: User,
        project: Project,
        type: IssueType,
        summary: str,
        description: Optional[str] = None,
        assignee: Optional[User] = None,
        parent_issue: Optional[Issue] = None,
        **kwargs,
    ) -> Issue:
        issue = Issue(
            id=len(project.issues) + 1,
            summary=summary,
            description=description,
            type=type,
            reporter=reporter,
            assignee=assignee,
            parentIssue=parent_issue,
            **kwargs,
        )
        return issue

    def get_current_project(self) -> Project:
        if len(self.workspace.projects) == 1:
            return self.workspace.projects[0]
        raise LookupError

    def create_issue_from_user_request(
        self, task_id: str, project: Project, input: str
    ):
        self.workspace.register_project_key_path(project.key, f"./{task_id}")
        user_proxy = project.project_leader
        issue = self.create_issue(
            reporter=user_proxy,
            project=project,
            type=IssueType.TASK,
            summary=input,
            assignee=user_proxy,
        )
        project.add_issue(issue)

        activity = IssueCreationActivity(created_by=user_proxy)
        issue.add_activity(activity)

        # NOTE: Originally added to address a LabelCsv issue, but has been deprecated due to updates in the benchmark.
        # comment = Comment(
        #     created_by=user_proxy,
        #     content="Strictly adhere to letter case in the assigned tasks; remember that 'Yellow' and 'yellow' are NOT the same.",
        # )
        # issue.add_activity(comment)

        file_infos = self.workspace.list_files_by_key(project.key)
        for file_info in file_infos:
            attachment = Attachment(
                url=file_info["relative_url"],
                filename=file_info["filename"],
                filesize=file_info["filesize"],
            )
            activty = AttachmentUploadActivity(
                created_by=user_proxy, attachment=attachment
            )
            issue.add_attachment(attachment)
            issue.add_activity(activty)

    async def execute_step(self, task_id: str, step_request: StepRequestBody) -> Step:
        """Execute a task step and update its status and output."""
        step = await self.next_step(task_id)
        if step is None:
            step = await self.db.create_step(task_id=task_id, input=step_request)
            step = await self.db.update_step(task_id, step.step_id, "running")

        if step_request.additional_input:
            project_key = step_request.additional_input.get("project_key", None)
            if project_key:
                project = self.workspace.get_project(project_key)
            raise ValueError
        else:
            project = self.get_current_project()

        if step_request.input:
            self.create_issue_from_user_request(task_id, project, step_request.input)

        print(project.display())

        unclosed_issues = [
            issue for issue in project.issues if issue.status != Status.CLOSED
        ]
        step_activities = []
        if len(unclosed_issues) > 0:
            project_leader: ProjectManagerAgentUser = project.project_leader
            worker, issue = await project_leader.select_worker(project)
            if issue.status in [Status.OPEN, Status.REOPENED]:
                activities = await worker.work_on_issue(project, issue)
            elif issue.status == Status.IN_PROGRESS:
                activities = await worker.resolve_issue(project, issue)
            elif issue.status == Status.RESOLVED:
                if worker.public_name != project_leader.public_name:
                    logger.error(
                        f"Warning: The issue is already resolved, but being accessed by {worker.public_name} who is not the project leader. Ensure the integrity of the resolution."
                    )
                    activities = await worker.resolve_issue(project, issue)
                else:
                    logger.info("reviewing")
                    activities = await worker.review_issue(project, issue)
            step_activities.extend(activities)

        for activity in step_activities:
            if isinstance(activity, AttachmentUploadActivity):
                await self.db.create_artifact(
                    task_id,
                    activity.attachment.filename,
                    activity.attachment.url,
                    agent_created=True,
                    step_id=step.step_id,
                )
            elif isinstance(activity, Comment):
                if activity.attachments:
                    for attachment in activity.attachments:
                        await self.db.create_artifact(
                            task_id,
                            attachment.filename,
                            attachment.url,
                            agent_created=True,
                            step_id=step.step_id,
                        )

        unclosed_issues = [
            issue for issue in project.issues if issue.status != Status.CLOSED
        ]

        step = await self.db.update_step(
            task_id,
            step.step_id,
            "completed",
            output=project.display(),
        )
        step.is_last = len(unclosed_issues) == 0
        return step

    async def next_step(self, task_id: str) -> Optional[Step]:
        steps, _ = await self.db.list_steps(
            task_id, per_page=int(os.environ.get("MAX_STEPS_PER_PAGE", 1000))
        )

        previous_steps = []
        pending_steps = []
        for step in steps:
            if step.status == StepStatus.created:
                pending_steps.append(step)
            elif step.status == StepStatus.completed:
                previous_steps.append(step)

        if len(pending_steps) > 0:
            return pending_steps.pop(0)
        return None
