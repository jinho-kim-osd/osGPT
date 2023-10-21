import json
from ..registry import ability
from ..schema import AbilityResult
from ...schema import Project, Issue, Attachment, AttachmentUploadActivity
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
    activity = AttachmentUploadActivity(created_by=agent, attachment=attachment)
    issue.add_attachment(attachment)
    issue.add_activity(activity)
    return AbilityResult(
        ability_name="create_python_file",
        ability_args={"file_name": file_name, "content": content},
        success=True,
        activities=[activity],
        attachments=[attachment],
    )
