from typing import Optional
from ..registry import ability
from ..schema import AbilityResult
from ...schema import (
    Comment,
    Project,
    Issue,
    IssueType,
    IssueLink,
    IssueLinkType,
    IssueCreationActivity,
    IssueDeletionActivity,
    IssueLinkCreationActivity,
    IssueLinkDeletionActivity,
    AssignmentChangeActivity,
    StatusChangeActivity,
    Status,
)


@ability(
    name="change_assignee",
    description="Change the assignee of a Jira issue",
    parameters=[
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
    new_assignee: str,
) -> AbilityResult:
    """
    Change the assignee of a specified Jira issue
    """
    new_assignee_name = new_assignee
    new_assignee_object = project.get_member(new_assignee_name).user
    old_assignee = issue.assignee

    if old_assignee.public_name == new_assignee_object.public_name:
        return AbilityResult(
            ability_name="change_assignee",
            ability_args={"new_assignee": new_assignee_name},
            success=False,
            message="The user is already assigned.",
        )

    issue.assignee = new_assignee_object

    activity = AssignmentChangeActivity(old_assignee=old_assignee, new_assignee=new_assignee_object, created_by=agent)
    issue.add_activity(activity)
    return AbilityResult(
        ability_name="change_assignee",
        ability_args={"new_assignee": new_assignee_name},
        success=True,
        activities=[activity],
    )


@ability(
    name="view_issue_details",
    description="View the details of a Jira issue",
    parameters=[
        {
            "name": "issue_id",
            "description": "ID of the issue to view details",
            "type": "number",
            "required": True,
        },
    ],
    output_type="object",
)
async def view_issue_details(agent, project: Project, issue: Issue, issue_id: int) -> AbilityResult:
    """
    View the details of a specified Jira issue
    """
    parent_issue = project.get_issue(issue_id)
    return AbilityResult(
        ability_name="view_issue_details",
        ability_args={"issue_id": issue_id},
        success=True,
        message=parent_issue.display(),
    )


@ability(
    name="add_comment",
    description="Add a comment to a Jira issue",
    parameters=[
        {
            "name": "content",
            "description": "Comment content",
            "type": "string",
            "required": True,
        },
    ],
    output_type="object",
)
async def add_comment(agent, project: Project, issue: Issue, content: str) -> AbilityResult:
    """
    Add a comment to a specified Jira issue
    """
    comment = Comment(content=content, created_by=agent)
    issue.add_activity(comment)
    return AbilityResult(
        ability_name="add_comment",
        ability_args={"content": content},
        success=True,
        activities=[comment],
    )


@ability(
    name="change_issue_status",
    description="Change the status of a Jira issue",
    parameters=[
        {
            "name": "old_status",
            "description": f"The current status of the issue",
            "type": "string",
            "enum": [e.value for e in Status if e != Status.CLOSED],
            "required": True,
        },
        {
            "name": "new_status",
            "description": f"The new status to be assigned to the issue",
            "type": "string",
            "enum": [e.value for e in Status if e != Status.CLOSED],
            "required": True,
        },
    ],
    output_type="object",
)
async def change_issue_status(
    agent,
    project: Project,
    issue: Issue,
    old_status: str,
    new_status: str,
) -> AbilityResult:
    """
    Change the status of a specified Jira issue
    """
    # Verifying if the new status is valid and applicable
    if not any(
        [transition for transition in project.workflow.transitions if transition.destination_status == new_status]
    ):
        raise ValueError(f"The status '{new_status}' is not a valid transition for the issue #{issue.id}")

    # Changing the status of the issue
    old_status = issue.status
    issue.status = Status(new_status)

    # Logging the status change as an activity
    activity = StatusChangeActivity(old_status=old_status, new_status=issue.status, created_by=agent)
    issue.add_activity(activity)
    return AbilityResult(
        ability_name="change_issue_status",
        ability_args={"old_status": old_status, "new_status": new_status},
        success=True,
        activities=[activity],
    )


@ability(
    name="close_issue",
    description="Close a Jira issue that is currently in a Resolved state",
    parameters=[
        {
            "name": "issue_id",
            "description": "ID of the issue to be closed",
            "type": "number",
            "required": True,
        },
    ],
    output_type="object",
)
async def close_issue(agent, project: Project, issue: Issue, issue_id: int) -> AbilityResult:
    """
    Close a specified Jira issue
    """
    closing_issue = project.get_issue(issue_id)

    if closing_issue.status != Status.RESOLVED:
        raise ValueError(f"Issue #{issue_id} is not resolved and cannot be closed.")

    old_status = closing_issue.status
    closing_issue.status = Status.CLOSED

    activity = StatusChangeActivity(old_status=old_status, new_status=closing_issue.status, created_by=agent)
    issue.add_activity(activity)
    return AbilityResult(
        ability_name="close_issue",
        ability_args={"issue_id": issue_id},
        success=True,
        activities=[activity],
    )


@ability(
    name="create_issue",
    description="Create a new Jira issue",
    parameters=[
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
            "enum": [e.value for e in IssueType if e != IssueType.EPIC],
            "required": True,
        },
        {
            "name": "parent_issue_id",
            "description": "If this issue is a subtask or related to another issue, provide the ID of the parent issue. This can be an Epic or any other issue type.",
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
    summary: str,
    assignee: str,
    type: str,
    parent_issue_id: Optional[int] = None,
) -> AbilityResult:
    """
    Create a new Jira issue with the specified summary, assignee, and type
    """
    # Getting the user from the workspace using the assignee username
    member = project.get_member(assignee)

    parent_issue = None
    if parent_issue_id is not None:
        parent_issue = project.get_issue(project.key, parent_issue_id)

    # Creating a new issue
    issue = Issue(
        id=len(project.issues) + 1,
        summary=summary,
        assignee=member.user,
        type=type,
        reporter=agent,
        parent_issue=parent_issue,
    )

    # Adding the issue to the workspace
    project.add_issue(issue)
    activity = IssueCreationActivity(created_by=agent)
    issue.add_activity(activity)
    return AbilityResult(
        ability_name="create_issue",
        ability_args={
            "summary": summary,
            "assignee": assignee,
            "type": type,
            "parent_issue_id": parent_issue_id,
        },
        success=True,
        activities=[activity],
    )


@ability(
    name="create_issue_link",
    description="Create a link between two Jira issues",
    parameters=[
        {
            "name": "source_issue_id",
            "description": "ID of the source issue",
            "type": "number",
            "required": True,
        },
        {
            "name": "target_issue_id",
            "description": "ID of the target issue",
            "type": "number",
            "required": True,
        },
        {
            "name": "link_type",
            "description": "Type of the link between the issues",
            "type": "string",
            "enum": [e.value for e in IssueLinkType],
            "required": True,
        },
    ],
    output_type="object",
)
async def create_issue_link(
    agent,
    project: Project,
    issue: Issue,
    source_issue_id: int,
    target_issue_id: int,
    link_type: str,
) -> AbilityResult:
    """
    Create a link between two specified Jira issues
    """
    source_issue = project.get_issue(source_issue_id)
    target_issue = project.get_issue(target_issue_id)
    link = IssueLink(
        type=IssueLinkType(link_type),
        source_issue=source_issue,
        target_issue=target_issue,
    )
    source_issue.links.append(link)
    # TODO: should we link target_issue?
    activity = IssueLinkCreationActivity(link=link, created_by=agent)
    issue.add_activity(activity)
    return AbilityResult(
        ability_name="create_issue",
        ability_args={
            "source_issue_id": source_issue_id,
            "target_issue_id": target_issue_id,
            "link_type": link_type,
        },
        success=True,
        activities=[activity],
    )


@ability(
    name="remove_issue_link",
    description="Remove a link between two Jira issues",
    parameters=[
        {
            "name": "source_issue_id",
            "description": "ID of the source issue",
            "type": "number",
            "required": True,
        },
        {
            "name": "target_issue_id",
            "description": "ID of the target issue",
            "type": "number",
            "required": True,
        },
    ],
    output_type="object",
)
async def remove_issue_link(
    agent,
    project: Project,
    issue: Issue,
    source_issue_id: int,
    target_issue_id: int,
) -> AbilityResult:
    """
    Remove a link between two specified Jira issues
    """
    source_issue = project.get_issue(source_issue_id)
    target_issue = project.get_issue(target_issue_id)
    link_to_remove = None

    for link in source_issue.links:
        if link.target_issue == target_issue:
            link_to_remove = link
            break

    if link_to_remove:
        source_issue.links.remove(link_to_remove)

    activity = IssueLinkDeletionActivity(link=link, created_by=agent)
    issue.add_activity(activity)  # TODO: should we add this activity to source and target issue?
    return AbilityResult(
        ability_name="create_issue",
        ability_args={
            "source_issue_id": source_issue_id,
            "target_issue_id": target_issue_id,
        },
        success=True,
        activities=[activity],
    )
