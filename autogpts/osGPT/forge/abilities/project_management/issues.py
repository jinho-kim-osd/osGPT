from typing import Optional, Dict
from ..registry import ability
from ...schema import (
    Comment,
    Workspace,
    Project,
    Issue,
    IssueType,
    AssignmentChangeActivity,
    StatusChangeActivity,
    Status,
)


@ability(
    name="change_assignee",
    description="Change the assignee of a Jira issue",
    parameters=[
        {
            "name": "project_key",
            "description": "Project Key",
            "type": "string",
            "required": True,
        },
        {
            "name": "issue_id",
            "description": "Issue ID",
            "type": "number",
            "required": True,
        },
        {
            "name": "new_assignee",
            "description": "New assignee username",
            "type": "string",
            "required": True,
        },
    ],
    output_type="object",
)
async def change_assignee(
    agent,
    project: Project,
    issue: Issue,
    project_key: str,
    issue_id: int,
    new_assignee: str,
) -> AssignmentChangeActivity:
    """
    Change the assignee of a specified Jira issue
    """
    target_issue = agent.workspace.get_issue(project_key, issue_id)
    old_assignee = target_issue.assignee
    new_assignee = agent.workspace.get_user_with_name(new_assignee)
    target_issue.assignee = new_assignee
    activity = AssignmentChangeActivity(
        old_assignee=old_assignee, new_assignee=new_assignee, created_by=agent
    )
    target_issue.add_activity(activity)
    return activity


@ability(
    name="add_comment",
    description="Add a comment to a Jira issue",
    parameters=[
        {
            "name": "project_key",
            "description": "Project Key",
            "type": "string",
            "required": True,
        },
        {
            "name": "issue_id",
            "description": "Issue ID",
            "type": "number",
            "required": True,
        },
        {
            "name": "content",
            "description": "Comment content",
            "type": "string",
            "required": True,
        },
    ],
    output_type="object",
)
async def add_comment(
    agent, project: Project, issue: Issue, project_key: str, issue_id: int, content: str
) -> Dict[str, str]:
    """
    Add a comment to a specified Jira issue
    """
    target_issue = agent.workspace.get_issue(project_key, issue_id)
    comment = Comment(content=content, created_by=agent)
    target_issue.add_activity(comment)
    return comment


@ability(
    name="change_issue_status",
    description="Change the status of a Jira issue",
    parameters=[
        {
            "name": "project_key",
            "description": "The key of the project containing the issue",
            "type": "string",
            "required": True,
        },
        {
            "name": "issue_id",
            "description": "The ID of the issue whose status is to be changed",
            "type": "number",
            "required": True,
        },
        {
            "name": "new_status",
            "description": f"The new status to be assigned to the issue",
            "type": "string",
            "enum": [e.value for e in Status],
            "required": True,
        },
    ],
    output_type="object",
)
async def change_issue_status(
    agent,
    project: Project,
    issue: Issue,
    project_key: str,
    issue_id: int,
    new_status: str,
) -> StatusChangeActivity:
    """
    Change the status of a specified Jira issue
    """
    target_project = agent.workspace.get_project_with_key(project_key)
    target_issue = agent.workspace.get_issue(project_key, issue_id)

    # Verifying if the new status is valid and applicable
    if not any(
        [
            transition
            for transition in target_project.workflow.transitions
            if transition.destination_status == new_status
        ]
    ):
        raise ValueError(
            f"The status '{new_status}' is not a valid transition for the issue #{issue_id}"
        )

    # Changing the status of the issue
    old_status = target_issue.status
    target_issue.status = Status(new_status)

    # Logging the status change as an activity
    activity = StatusChangeActivity(
        old_status=old_status, new_status=new_status, created_by=agent
    )
    target_issue.add_activity(activity)
    return activity


@ability(
    name="create_issue",
    description="Create a new Jira issue",
    parameters=[
        {
            "name": "project_key",
            "description": "Project Key",
            "type": "string",
            "required": True,
        },
        {
            "name": "summary",
            "description": "Issue summary",
            "type": "string",
            "required": True,
        },
        {
            "name": "assignee",
            "description": "Assignee username",
            "type": "string",
            "required": True,
        },
        {
            "name": "type",
            "description": "Issue type",
            "type": "string",
            "enum": [e.value for e in IssueType],
            "required": True,
        },
        {
            "name": "parent_issue_id",
            "description": "Parent Issue ID (Issue type must be SUBTASK when a parent issue is provided)",
            "type": "number",
            "required": False,
        },
    ],
    output_type="object",
)
async def create_issue(
    agent,
    project: Project,
    issue: Issue,
    project_key: str,
    summary: str,
    assignee: str,
    type: str,
    parent_issue_id: Optional[int] = None,
) -> Issue:
    """
    Create a new Jira issue with the specified summary, assignee, and type
    """
    # Getting the project from the workspace using the project_key
    project = agent.workspace.get_project_with_key(project_key)

    # Getting the user from the workspace using the assignee username
    assignee_user = agent.workspace.get_user_with_name(assignee)

    parent_issue = None
    if parent_issue_id is not None:
        parent_issue = agent.workspace.get_issue(project_key, parent_issue_id)

    # Creating a new issue
    issue = Issue(
        id=len(project.issues) + 1,
        summary=summary,
        assignee=assignee_user,
        type=type,
        reporter=agent,
        parent_issue=parent_issue,
    )

    # Ensure the issue type is SUBTASK if a parent issue is provided
    if parent_issue is not None and issue.type != IssueType.SUBTASK:
        raise ValueError("Issue type must be SUBTASK when a parent issue is provided")

    # Adding the issue to the workspace
    project.add_issue(issue)

    return issue
