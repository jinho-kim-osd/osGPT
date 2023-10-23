from ..registry import ability
from ..schema import AbilityResult
from ...schema import (
    Project,
    Issue,
    IssueType,
    Attachment,
    Comment,
)
from forge.sdk import ForgeLogger

logger = ForgeLogger(__name__)


@ability(
    name="write_code",
    description="Create or update a Python file with the provided content in the workspace.",
    parameters=[
        {
            "name": "file_name",
            "description": "Name of the Python file to be created or updated.",
            "type": "string",
            "required": True,
        },
        {
            "name": "content",
            "description": "Content to be written to the Python file.",
            "type": "string",
            "required": True,
        },
    ],
    output_type="object",
)
async def write_code(agent, project: Project, issue: Issue, file_name: str, content: str) -> AbilityResult:
    """
    Create or update a Python file and write the provided content to it.
    A code review will be initiated for new files only.
    """
    activities = []

    project_root = agent.workspace.get_project_path_by_key(project.key)
    file_path = project_root / file_name

    # Determine if the file already exists
    existing_files = agent.workspace.list_files_by_key(key=project.key, path=file_path.parent)
    existing_file = next((f for f in existing_files if f["filename"] == file_name), None)

    # Write the content to the file
    if isinstance(content, str):
        content = content.encode()

    file_info = agent.workspace.write_file_by_key(key=project.key, path=file_path, data=content)

    new_attachment = Attachment(
        url=file_info.relative_url,
        filename=file_info.filename,
        filesize=file_info.filesize,
    )
    issue.add_attachment(new_attachment, agent)

    # Determine the appropriate activity and comment based on whether the file already exists
    if existing_file:
        # Add a comment indicating the status of the code and if a review is being initiated
        comment = Comment(
            created_by=agent,
            content=f"The file '{file_name}' has been updated.",
            attachments=[new_attachment],
        )
        issue.add_activity(comment)

    else:
        development_issue = Issue(
            id=len(project.issues) + 1,
            summary=f"Review a '{file_name}' file for alignment with the requirements",
            project_key=project.key,
            reporter=agent,
            parent_issue=issue,
            assignee=agent,
            type=IssueType.TASK,
        )
        project.add_issue(development_issue)
        development_issue.add_attachment(new_attachment, agent)

        # Add a comment indicating the status of the code and if a review is being initiated
        comment = Comment(
            created_by=agent,
            content=f"New file '{file_name}' created. I'm initiating an immediate review to ensure it meets all requirements.",
            attachments=[new_attachment],
        )
        development_issue.add_activity(comment)

    issue.add_attachment(new_attachment, agent)
    upload_activity = issue.get_last_activity()

    return AbilityResult(
        ability_name="write_code",
        ability_args={"file_name": file_name, "content": content},
        success=True,
        activities=[upload_activity, comment],
        attachments=[new_attachment],
    )


def conduct_unit_tests():
    ...


def review_code():
    ...
