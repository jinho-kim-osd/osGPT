import os
from forge.sdk import LocalWorkspace
from .agent_user import AgentUser
from .predefined_users.project_manager_agent import ProjectManagerAgentUser
from .workspace import Workspace
from .db import ForgeDatabase
from .schema import Role, Transition, Status, Workflow, Project


def setup_workspace(db: ForgeDatabase) -> Workspace:
    """
    Setup and return a workspace with predefined agents, roles, and a sample project.

    Args:
        db (ForgeDatabase): The database instance for storing workspace data.

    Returns:
        Workspace: The configured workspace.
    """
    # Create a workspace with a service pointing to a local directory.
    workspace = Workspace(name=os.getenv("WORKSPACE_NAME"), service=LocalWorkspace(os.getenv("WORKSPACE_BASE_PATH")))
    workspace.reset()

    # Create project manager agent with specified abilities.
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
            "finish_work",
        ],
        db=db,
    )

    # Create document specialist agent with specified abilities.
    document_specialist = AgentUser(
        public_name="Jinho Kim",
        job_title="Data Handling Expert",
        workspace=workspace,
        ability_names=[
            "change_issue_status",
            "add_comment",
            "read_file",
            "write_file",
            "list_files",
            "detect_csv_separator",
            "read_csv",
            "run_python_code",
            "finish_work",
        ],
        db=db,
    )

    # Create software engineer agent with specified abilities.
    engineer = AgentUser(
        public_name="Max Dillon",
        job_title="Software Development Specialist",
        workspace=workspace,
        ability_names=[
            "change_issue_status",
            "add_comment",
            "read_file",
            "write_file",
            "list_files",
            "design_system_architecture",
            "read_system_architecture",
            # "write_code",
            "finish_work",
        ],
        db=db,
    )

    # Create information retrieval specialist agent with specified abilities.
    researcher = AgentUser(
        public_name="Jiyeon Lee",
        job_title="Information Retrieval Specialist",
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

    # Define the workflow transitions.
    transitions = [
        Transition(name="Start Progress", source_status=Status.OPEN, destination_status=Status.IN_PROGRESS),
        Transition(name="Mark Resolved", source_status=Status.IN_PROGRESS, destination_status=Status.RESOLVED),
        Transition(name="Reopen", source_status=Status.RESOLVED, destination_status=Status.REOPENED),
        Transition(name="Close", source_status=Status.REOPENED, destination_status=Status.CLOSED),
    ]

    # Create a workflow with the defined transitions.
    workflow = Workflow(name="Default Workflow", transitions=transitions)

    # Create a project and set its workflow.
    project = Project(key="AHC", name="Arena Hacks Challenge 2023", project_leader=project_manager, workflow=workflow)
    workspace.add_project(project)

    # Add members to the project with their respective roles.
    project.add_member(project_manager, Role.ADMIN)
    project.add_member(document_specialist, Role.MEMBER)
    project.add_member(engineer, Role.MEMBER)
    project.add_member(researcher, Role.MEMBER)

    return workspace
