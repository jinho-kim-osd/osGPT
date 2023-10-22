from ...registry import ability
from ...schema import AbilityResult
from ....schema import Project, Issue, Attachment, AttachmentUploadActivity, AttachmentUpdateActivity, Comment
from forge.sdk import ForgeLogger

logger = ForgeLogger(__name__)


@ability(
    name="write_code",
    description="Create a new Python file with the provided content in the workspace.",
    parameters=[
        {
            "name": "file_name",
            "description": "Name of the Python file to be created.",
            "type": "string",
            "required": True,
        },
        {
            "name": "content",
            "description": "Content to be written to the new Python file.",
            "type": "string",
            "required": True,
        },
    ],
    output_type="object",
)
async def write_code(
    agent, project: Project, issue: Issue, file_name: str, content: str
) -> AbilityResult:
    """
    Create or update a Python file and write the provided content to it, then proceed with the code review.
    """
    # Check if the file_name ends with '.py', if not append it
    if not file_name.endswith(".py"):
        file_name += ".py"

    project_root = agent.workspace.get_project_path_by_key(project.key)
    file_path = project_root / file_name

    # Check if the file already exists
    existing_files = agent.workspace.list_files_by_key(key=project.key, path=file_path.parent)
    existing_file = next((f for f in existing_files if f['filename'] == file_name), None)

    if isinstance(content, str):
        content = content.encode()

    file_info = agent.workspace.write_file_by_key(
        key=project.key, path=file_path, data=content
    )

    new_attachment = Attachment(
        url=file_info["relative_url"],
        filename=file_info["filename"],
        filesize=file_info["filesize"],
    )

    if existing_file:
        old_attachment = Attachment(
            url=existing_file["relative_url"],
            filename=existing_file["filename"],
            filesize=existing_file["filesize"],
        )
        update_activity = AttachmentUpdateActivity(created_by=agent, old_attachment=old_attachment, new_attachment=new_attachment)
    else:
        update_activity = AttachmentUploadActivity(created_by=agent, attachment=new_attachment)
    
    issue.add_activity(update_activity)
    issue.add_attachment(new_attachment)

    # Add comment to force review code
    comment = Comment(
        created_by=agent,
        content="I've updated the code. Initiating the code review process to ensure quality and adherence to requirements.",
        attachments=[new_attachment],
    )
    issue.add_activity(comment)

    return AbilityResult(
        ability_name="write_code",
        ability_args={"file_name": file_name, "content": content},
        success=True,
        message="Code updated successfully, initiating review.",
        activities=[update_activity, comment],
        attachments=[new_attachment],
    )