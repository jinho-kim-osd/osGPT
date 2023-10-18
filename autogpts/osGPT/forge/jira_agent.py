from typing import Optional, List, Tuple, Any
from forge.sdk import (
    Agent,
    Task,
    Step,
    StepRequestBody,
    ForgeLogger,
    Status as StepStatus,
)
from forge.sdk.abilities.registry import AbilityRegister
from .project_manager_agent import ProjectManagerAgentUser
from .schema import (
    User,
    Role,
    Transition,
    Status,
    Workflow,
    Project,
    Issue,
    IssueType,
    Comment,
    Activity,
    IssueCreationActivity,
    AttachmentUploadActivity,
    Attachment,
    WorkspaceMember,
)
from .agent_user import AgentUser
from .db import ForgeDatabase
from .workspace import CollaborationWorkspace
from .contants import (
    LIST_STEPS_PER_PAGE,
    DEFAULT_USER_ID,
    DEFAULT_USER_NAME,
    DEFAULT_USER_ABILITIES,
)

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
        self.workspace.reset()

        # Creating users
        self.user_proxy_agent = AgentUser(
            id=DEFAULT_USER_ID,
            name=DEFAULT_USER_NAME,
            role=Role.MEMBER,
            workspace=self.workspace,
            ability_names=DEFAULT_USER_ABILITIES,
            db=self.db,
        )
        project_manager = ProjectManagerAgentUser(
            id="project_manager",
            name="Norman Osborn",
            role=Role.ADMIN,
            workspace=self.workspace,
            ability_names=[*DEFAULT_USER_ABILITIES, "change_assignee", "finish"],
            db=self.db,
        )
        engineer = AgentUser(
            id="engineer",
            name="Max Dillon",
            role=Role.MEMBER,
            workspace=self.workspace,
            ability_names=[*DEFAULT_USER_ABILITIES, "run_python_code"],
            db=self.db,
        )

        # Add members to a Workspace
        for user, workspace_role in zip(
            [self.user_proxy_agent, project_manager, engineer],
            ["Problem Provider", "Project Manager", "Enginner"],
        ):
            self.workspace.add_member(user, workspace_role)

        # Creating a Workflow with Transitions
        transitions = [
            Transition(
                name="Start Progress",
                source_status=Status.OPEN,
                destination_status=Status.IN_PROGRESS,
            ),
            Transition(
                name="Mark Resolved",
                source_status=Status.IN_PROGRESS,
                destination_status=Status.RESOLVED,
            ),
            Transition(
                name="Reopen",
                source_status=Status.RESOLVED,
                destination_status=Status.REOPENED,
            ),
            Transition(
                name="Close",
                source_status=Status.REOPENED,
                destination_status=Status.CLOSED,
            ),
        ]
        workflow = Workflow(name="Default Workflow", transitions=transitions)

        # Creating a project and adding the issue to it
        project = Project(
            key="AAH",
            name="AutoGPT Arena Hacks",
            project_leader=project_manager,
            workflow=workflow,
        )
        self.workspace.add_project(project)

        # issue = Issue(
        #     id=1, summary="test", type=IssueType.TASK, reporter=self.user_proxy_agent
        # )
        # attachment = Attachment(
        #     url="/Users/jinho/Projects/osGPT/autogpts/osGPT/input.txt",
        #     filename="input.txt",
        #     filesize=3153,
        # )
        # issue.add_activity(
        #     Comment(
        #         content="test",
        #         created_by=self.user_proxy_agent,
        #         attachments=[attachment],
        #     )
        # )

    @property
    def workspace_member_user_ids(self) -> List[str]:
        return [member.user.id for member in self.workspace.members]

    def get_member_by_id(self, id: str) -> WorkspaceMember:
        return self.workspace.members[self.workspace_member_user_ids.index(id)]

    def reset(self):
        self.setup_workspace()

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

    def set_agent_protocol(self, task: Task, step: Step):
        self.current_task = task
        self.current_step = step
        for member in self.workspace.users:
            member.set_agent_protocol(task, step)

    def get_current_project(self) -> Project:
        if len(self.workspace.projects) == 1:
            return self.workspace.projects[0]
        raise LookupError

    def get_current_project(self) -> Project:
        if len(self.workspace.projects) == 1:
            return self.workspace.projects[0]
        raise LookupError

    async def execute_step(self, task_id: str, step_request: StepRequestBody) -> Step:
        """Execute a task step and update its status and output."""
        task = await self.db.get_task(task_id)

        all_steps, step = await self.next_step(task_id)
        if step is None:
            step = await self.db.create_step(task_id=task_id, input=step_request)

        if step.status == StepStatus.created:
            step = await self.db.update_step(task_id, step.step_id, "running")

        if step_request.additional_input:
            project_name = step_request.additional_input.get("project_name", None)
            if project_name:
                project = self.workspace.get_project(project_name)
            raise ValueError
        else:
            project = self.get_current_project()

        if step_request.input:
            num_issues = len(project.issues)
            issue = Issue(
                id=num_issues + 1,
                summary=step_request.input,
                type=IssueType.TASK,
                assignee=project.project_leader,
                reporter=self.user_proxy_agent,
            )
            activity = IssueCreationActivity(created_by=self.user_proxy_agent)
            issue.add_activity(activity)

            existing_attachments = self.workspace.list_attachments(task_id, ".")
            for attachment in existing_attachments:
                issue.add_attachment(attachment)

            issue.add_activity(
                Comment(content=step_request.input, created_by=self.user_proxy_agent)
            )
            project.add_issue(issue)

            # clarify user requirements
            response = project.project_leader.clarify_requirements(
                step_request.input, project, issue
            )
            ...
        else:
            for pending_issue in project.issues:
                if pending_issue.status in [Status.OPEN, Status.IN_PROGRESS]:
                    issue = pending_issue
                    break

        # Printing the workspace structure
        print(self.workspace.display_structure())
        activities = await issue.assignee.execute_project(task_id, project, issue)
        for activity in activities:
            if isinstance(activity, Comment):
                if activity.attachments:
                    for attachment in activity.attachments:
                        self.db.create_artifact(
                            task_id,
                            attachment.filename,
                            relative_path=attachment.url,
                            agent_created=True,
                            step_id=step.step_id,
                        )

        step = await self.db.update_step(
            task_id,
            step.step_id,
            "completed",
            output=self.workspace.display_structure(),
        )
        step.is_last = True
        print(self.workspace.display_structure())
        return step

    async def next_step(self, task_id: str) -> Tuple[List[Step], Optional[Step]]:
        steps, _ = await self.db.list_steps(task_id, per_page=LIST_STEPS_PER_PAGE)

        previous_steps = []
        pending_steps = []
        for step in steps:
            if step.status == StepStatus.created:
                pending_steps.append(step)
            elif step.status == StepStatus.completed:
                previous_steps.append(step)

        if pending_steps:
            return steps, pending_steps.pop(0)
        return steps, None
