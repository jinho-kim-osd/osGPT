import os

from forge.sdk import LocalWorkspace

from .agent_user import AgentUser
from .project_manager_agent import ProjectManagerAgentUser
from .workspace import Workspace
from .db import ForgeDatabase
from .schema import (
    Role,
    Transition,
    Status,
    Workflow,
    Project,
    Comment,
    Epic,
    Issue,
    IssueType,
    Attachment,
    IssueLink,
    IssueLinkType,
    IssueLinkCreationActivity,
    IssueCreationActivity,
    AttachmentUploadActivity,
)


def setup_workspace(db: ForgeDatabase) -> Workspace:
    workspace = Workspace(
        name=os.getenv("DEFAULT_WORKSPACE_NAME"),
        service=LocalWorkspace(os.getenv("WORKSPACE_BASE_PATH")),
    )
    workspace.reset()

    project_manager = ProjectManagerAgentUser(
        public_name="Norman Osborn",
        job_title="Project Manager",
        workspace=workspace,
        ability_names=[
            "read_file",
            "list_files",
            "change_issue_status",
            "close_issue",
            "add_comment",
            "create_issue",
            "change_assignee",
            # "create_issue_link",
            # "remove_issue_link",
            "finish_work",
        ],
        db=db,
    )
    engineer = AgentUser(
        public_name="Max Dillon",
        job_title="Engineer",
        workspace=workspace,
        ability_names=[
            "read_file",
            "list_files",
            "change_issue_status",
            "add_comment",
            "run_python_code",
            "finish_work",
        ],
        db=db,
    )

    researcher = AgentUser(
        public_name="Jiyeon Lee",
        job_title="Internet Researcher",
        workspace=workspace,
        ability_names=[
            "read_file",
            "write_file",
            "list_files",
            "change_issue_status",
            "add_comment",
            "web_search",
            "read_webpage",
            "finish_work",
        ],
        db=db,
    )

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

    # Creating a project
    project = Project(
        key="AHC",
        name="Arena Hacks Challenge 2023",
        project_leader=project_manager,
        workflow=workflow,
    )
    workspace.add_project(project)

    project.add_member(project_manager, Role.ADMIN)
    project.add_member(engineer, Role.MEMBER)
    project.add_member(researcher, Role.MEMBER)
    return workspace
