from ...registry import ability
from ...schema import AbilityResult
from ....schema import Project, Issue, Attachment, AttachmentUploadActivity, Comment
from forge.sdk import ForgeLogger

logger = ForgeLogger(__name__)


@ability(
    name="create_python_file",
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
async def create_python_file(
    agent, project: Project, issue: Issue, file_name: str, content: str
) -> AbilityResult:
    """
    Create a new Python file and write the provided content to it
    """
    # Check if the file_name ends with '.py', if not append it
    if not file_name.endswith(".py"):
        file_name += ".py"

    project_root = agent.workspace.get_project_path_by_key(project.key)
    file_path = project_root / file_name

    if isinstance(content, str):
        content = content.encode()

    file_info = agent.workspace.write_file_by_key(
        key=project.key, path=file_path, data=content
    )

    attachment = Attachment(
        url=file_info["relative_url"],
        filename=file_info["filename"],
        filesize=file_info["filesize"],
    )
    upload_activity = AttachmentUploadActivity(created_by=agent, attachment=attachment)
    issue.add_activity(upload_activity)

    comment = Comment(
        created_by=agent,
        content="I've written the code in the file. Now, I'm proceeding with the code review.",
        attachments=[attachment],
    )
    issue.add_activity(comment)
    issue.add_attachment(attachment)
    
    return AbilityResult(
        ability_name="create_python_file",
        ability_args={"file_name": file_name, "content": content},
        success=True,
        message="File created successfully.",
        activities=[upload_activity, comment],
        attachments=[attachment],
    )

@ability(
    name="update_python_file",
    description="Update an existing Python file with the provided content in the workspace.",
    parameters=[
        {
            "name": "file_name",
            "description": "Name of the Python file to be updated.",
            "type": "string",
            "required": True,
        },
        {
            "name": "content",
            "description": "New content to be written to the existing Python file.",
            "type": "string",
            "required": True,
        },
    ],
    output_type="object",
)
async def update_python_file(
    agent, project: Project, issue: Issue, file_name: str, content: str
) -> AbilityResult:
    """
    Update an existing Python file and write the provided content to it
    """
    # Check if the file_name ends with '.py', if not append it
    if not file_name.endswith(".py"):
        file_name += ".py"

    project_root = agent.workspace.get_project_path_by_key(project.key)
    file_path = project_root / file_name

    # Additional check to ensure the file exists before attempting to update it
    if not file_path.exists():
        raise FileNotFoundError(f"The file '{file_name}' does not exist.")

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
    for old_attachment in issue.attachments:
        if old_attachment.filename == new_attachment.filename:
            issue.remove_attachment(old_attachment)
            break
    upload_activity = AttachmentUploadActivity(created_by=agent, attachment=new_attachment)
    issue.add_activity(upload_activity)

    comment = Comment(
        created_by=agent,
        content=f"I've updated the code in {file_name}.",
        attachments=[new_attachment],
    )
    issue.add_activity(comment)
    issue.add_attachment(new_attachment)
    
    return AbilityResult(
        ability_name="update_python_file",
        ability_args={"file_name": file_name, "content": content},
        success=True,
        message="File updated successfully.",
        activities=[upload_activity, comment],
        attachments=[new_attachment],
    )
