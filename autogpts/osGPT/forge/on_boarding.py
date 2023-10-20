import os

from forge.sdk import LocalWorkspace

from .agent_user import AgentUser
from .project_manager_agent import ProjectManagerAgentUser
from .workspace import CollaborationWorkspace
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


def setup_workspace(db: ForgeDatabase) -> CollaborationWorkspace:
    workspace = CollaborationWorkspace(
        name=os.getenv("DEFAULT_WORKSPACE_NAME"),
        service=LocalWorkspace(os.getenv("WORKSPACE_BASE_PATH")),
    )
    workspace.reset()

    # Creating users
    user_proxy_agent = AgentUser(
        id=os.environ.get("DEFAULT_USER_ID"),
        name=os.environ.get("DEFAULT_USER_NAME"),
        role=Role.OWNER,
        workspace=workspace,
        ability_names=[
            # "read_file",
            # "list_files",
            # "change_issue_status",
            "add_comment",
        ],
        db=db,
    )
    project_manager = ProjectManagerAgentUser(
        id="norman_osborn",
        name="Norman Osborn",
        role=Role.ADMIN,
        workspace=workspace,
        ability_names=[
            "read_file",
            "list_files",
            "change_issue_status",
            "add_comment",
            "create_issue",
            "change_assignee",
            "create_issue_link",
            "remove_issue_link",
            "finish_work",
        ],
        db=db,
    )
    engineer = AgentUser(
        id="max_dillon",
        name="Max Dillon",
        role=Role.MEMBER,
        workspace=workspace,
        ability_names=[
            "read_file",
            "list_files",
            "change_issue_status",
            "add_comment",
            "create_issue_link",
            "remove_issue_link",
            "run_python_code",
            "finish_work",
        ],
        db=db,
    )

    # Add members to a Workspace with workspace role
    for user, workspace_role in zip(
        [user_proxy_agent, project_manager, engineer],
        ["Boss", "Project Manager", "Engineer"],
    ):
        workspace.add_member(user, workspace_role)

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
        key="AHC",
        name="Arena Hacks Challenge 2023",
        project_leader=project_manager,
        workflow=workflow,
    )
    workspace.add_project(project)

    # Test
    epic_issue = Epic(
        id=len(project.issues) + 1,
        summary="Arana Hacks Challenges",
        description="Participants will tackle a series of tasks, emphasizing real-world application of data handling, programming, web scraping, and versatile problem-solving skills. Each task is tailored to elevate in complexity, pushing the boundaries of innovation and technical expertise.",
        assignee=project.project_leader,
        reporter=user_proxy_agent,
        status=Status.IN_PROGRESS,
    )
    activity = IssueCreationActivity(created_by=user_proxy_agent)
    epic_issue.add_activity(activity)
    project.add_issue(epic_issue)

    issue = Issue(
        id=len(project.issues) + 1,
        summary="Write a word 'Washington' to .txt file.",
        description="These resources cover everything from setting up AutoGPT to using it for specific applications and creating your own AI agents. Feel free to join the AutoGPT Discord for communication and mentorship throughout the hackathon.",
        type=IssueType.TASK,
        assignee=project.project_leader,
        reporter=user_proxy_agent,
        parent_issue=epic_issue,
        child_issues=[epic_issue, epic_issue],
    )
    epic_issue.add_link(IssueLinkType.IS_BLOCKED_BY, issue)
    issue.add_link(IssueLinkType.BLOCKS, epic_issue)
    project.add_issue(issue)
    activity = IssueCreationActivity(created_by=user_proxy_agent)
    issue.add_activity(activity)

    existing_attachments = workspace.list_attachments(f".")
    for attachment in existing_attachments:
        activty = AttachmentUploadActivity(
            created_by=user_proxy_agent, attachment=attachment
        )
        issue.add_attachment(attachment)
        issue.add_activity(activty)

    issue.add_activity(
        Comment(
            content=f"Workspace Root Path: ./",
            created_by=user_proxy_agent,
        )
    )
    print(issue.display())
    return workspace
