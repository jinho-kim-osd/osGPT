from typing import Dict
from ..registry import ability
from ...schema import Comment, Workspace, AssignmentChangeActivity


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
    agent, workspace: Workspace, project_key: str, issue_id: int, new_assignee: str
) -> AssignmentChangeActivity:
    """
    Change the assignee of a specified Jira issue
    """
    target_issue = workspace.get_issue(project_key, issue_id)
    old_assignee = target_issue.assignee
    new_assignee = workspace.get_user_with_name(new_assignee)
    target_issue.assignee = new_assignee
    activity = AssignmentChangeActivity(
        old_assignee=old_assignee, new_assignee=new_assignee, created_by=agent
    )
    target_issue.add_activity(activity)
    return AssignmentChangeActivity


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
    agent, workspace: Workspace, project_key: str, issue_id: int, content: str
) -> Dict[str, str]:
    """
    Add a comment to a specified Jira issue
    """
    target_issue = workspace.get_issue(project_key, issue_id)
    comment = Comment(content=content, created_by=agent)
    target_issue.add_activity(comment)
    return comment
