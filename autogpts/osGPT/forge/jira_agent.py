import os
from typing import Optional, List, Tuple, Any
from forge.sdk import (
    Agent,
    Step,
    StepRequestBody,
    ForgeLogger,
    Status as StepStatus,
)
from forge.sdk.abilities.registry import AbilityRegister
from .schema import (
    User,
    Status,
    Project,
    Issue,
    IssueType,
    Comment,
    IssueCreationActivity,
)
from .project_manager_agent import ProjectManagerAgentUser
from .agent_user import AgentUser
from .db import ForgeDatabase
from .workspace import CollaborationWorkspace


logger = ForgeLogger(__name__)


class JiraAgent(Agent):
    """
    An agent designed to emulate Jira or other project management systems, capable of being
    replaced by or integrated with actual systems for real-world application and use.
    """

    def __init__(
        self,
        database: ForgeDatabase,
        workspace: CollaborationWorkspace,
    ):
        self.db = database
        self.workspace = workspace
        self.abilities = AbilityRegister(self, None)

    def setup_workspace(self):
        self.user_proxy_agent = self.workspace.get_user_with_name(
            os.environ.get("DEFAULT_USER_NAME")
        )

    def reset(self):
        # Remove all issues
        for project in self.workspace.projects:
            project.issues = []

    async def create_issue(
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
        initial_input = f"Plan and assign issues for executing '{input}'"
        issue = Issue(
            id=len(project.issues) + 1,
            summary=initial_input,
            type=IssueType.TASK,
            assignee=project.project_leader,
            reporter=self.user_proxy_agent,
        )
        activity = IssueCreationActivity(created_by=self.user_proxy_agent)
        issue.add_activity(activity)

        existing_attachments = self.workspace.list_attachments(f"{task_id}/.")
        for attachment in existing_attachments:
            issue.add_attachment(attachment)

        issue.add_activity(
            Comment(
                content=f"Workspace Root Path: ./{task_id}",
                created_by=self.user_proxy_agent,
            )
        )
        project.add_issue(issue)

    async def execute_step(self, task_id: str, step_request: StepRequestBody) -> Step:
        """Execute a task step and update its status and output."""
        step = await self.next_step(task_id)
        if step is None:
            step = await self.db.create_step(task_id=task_id, input=step_request)
            step = await self.db.update_step(task_id, step.step_id, "running")

        if step_request.additional_input:
            project_name = step_request.additional_input.get("project_name", None)
            if project_name:
                project = self.workspace.get_project(project_name)
            raise ValueError
        else:
            project = self.get_current_project()

        if step_request.input:
            self.create_issue_from_user_request(task_id, project, step_request.input)

        unclosed_issues = [
            issue for issue in project.issues if issue.status != Status.CLOSED
        ]
        step_activities = []
        if len(unclosed_issues) > 0:
            project_leader: ProjectManagerAgentUser = project.project_leader
            worker = await project_leader.select_worker(project)
            issue = await worker.select_issue(project)
            if project_leader != worker and issue.assignee != worker:
                raise ValueError  # For Debugging
            if issue.status in [Status.OPEN, Status.REOPENED]:
                activities = worker.work_on_issue(project, issue)
            elif issue.status == Status.IN_PROGRESS:
                activities = worker.resolve_issue(project, issue)
            elif issue.status == Status.RESOLVED:
                if worker != project_leader:
                    raise ValueError
                activities = worker.review_issue(project, issue)
            elif issue.status == Status.CLOSED:
                raise NotImplementedError
                activities = worker.decide_reopen(project, issue)
            step_activities.extend(activities)

        step = await self.db.update_step(
            task_id,
            step.step_id,
            "completed",
            output=self.workspace.display(),
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
