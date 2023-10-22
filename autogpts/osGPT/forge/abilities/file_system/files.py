import json

from ..registry import ability
from ..schema import AbilityResult
from ...schema import Project, Issue, Attachment, AttachmentUploadActivity, AttachmentUpdateActivity
from forge.sdk import ForgeLogger

logger = ForgeLogger(__name__)


@ability(
    name="list_files",
    description="List all files in the specified or current directory within the workspace.",
    parameters=[
        {
            "name": "dir_path",
            "description": "The directory path relative to the workspace, defaults to the current directory.",
            "type": "string",
            "required": False,
            "default": ".",
        }
    ],
    output_type="object",
)
async def list_files(
    agent, project: Project, issue: Issue, dir_path: str = "."
) -> AbilityResult:
    """
    List files in the specified or current directory within the workspace.
    """
    file_infos = agent.workspace.list_files_by_key(key=project.key, path=dir_path)
    file_names = [info["filename"] for info in file_infos]

    if not file_names:
        return AbilityResult(
            ability_name="list_files",
            ability_args={"dir_path": dir_path},
            message=f"No files found in the directory '{dir_path}'.",
            success=True,
        )

    return AbilityResult(
        ability_name="list_files",
        ability_args={"dir_path": dir_path},
        message=f"Files in '{dir_path}': {', '.join(file_names)}",
        success=True,
    )


@ability(
    name="write_file",
    description="Write data to a file within the workspace.",
    parameters=[
        {
            "name": "file_path",
            "description": "Relative path to the file.",
            "type": "string",
            "required": True,
        },
        {
            "name": "data",
            "description": "Data to write to the file",
            "type": "string",
            "required": True,
        },
    ],
    output_type="object",
)
async def write_file(
    agent, project: Project, issue: Issue, file_path: str, data: str
) -> AbilityResult:
    """
    Write data to a file
    """
    file_infos = agent.workspace.list_files_by_key(key=project.key, path=Path(file_path).parent)
    existing_file_info = next((info for info in file_infos if info["filename"] == Path(file_path).name), None)

    if isinstance(data, str):
        data = data.encode()

    file_info = agent.workspace.write_file_by_key(
        key=project.key, path=file_path, data=data
    )
    new_attachment = Attachment(
        url=file_info["relative_url"],
        filename=file_info["filename"],
        filesize=file_info["filesize"],
    )


    if existing_file_info:
        old_attachment = Attachment(
            url=existing_file_info["relative_url"],
            filename=existing_file_info["filename"],
            filesize=existing_file_info["filesize"],
        )
        update_activity = AttachmentUpdateActivity(
            created_by=agent, old_attachment=old_attachment, new_attachment=new_attachment
        )
    else:
        update_activity = AttachmentUploadActivity(created_by=agent, attachment=new_attachment)

    issue.add_attachment(new_attachment)
    issue.add_activity(update_activity)
    
    return AbilityResult(
        ability_name="write_file",
        ability_args={"file_path": file_path, "data": data},
        success=True,
        activities=[update_activity],
        attachments=[new_attachment],
    )


@ability(
    name="read_file",
    description="Read data from a specific file within the workspace.",
    parameters=[
        {
            "name": "file_path",
            "description": "Path to the file.",
            "type": "string",
            "required": True,
        },
    ],
    output_type="bytes",
)
async def read_file(
    agent, project: Project, issue: Issue, file_path: str
) -> AbilityResult:
    """
    Read data from a file
    """
    data = agent.workspace.read_by_key(key=project.key, path=file_path)
    if isinstance(data, bytes):
        data = data.decode("utf-8")
    return AbilityResult(
        ability_name="read_file",
        ability_args={"file_path": file_path},
        success=True,
        message=json.dumps(data),
    )
