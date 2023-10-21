from typing import List

from ..registry import ability
from ..schema import AbilityResult
from ...schema import Project, Issue, Attachment, AttachmentUploadActivity
from forge.sdk import ForgeLogger

logger = ForgeLogger(__name__)


@ability(
    name="list_files",
    description="List files in a workspace",
    parameters=[
        {
            "name": "dir_path",
            "description": "Relative directory path to list files.",
            "type": "string",
            "required": True,
        }
    ],
    output_type="object",
)
async def list_files(
    agent, project: Project, issue: Issue, dir_path: str
) -> AbilityResult:
    """
    List files in a workspace directory
    """
    file_infos = agent.workspace.list_files_by_key(key=project.key, path=dir_path)
    file_names = [info["filename"] for info in file_infos]
    return AbilityResult(
        ability_name="list_files",
        ability_args={"dir_path": dir_path},
        message=str(file_names),
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
    if isinstance(data, str):
        data = data.encode()

    file_info = agent.workspace.write_file_by_key(
        key=project.key, path=file_path, data=data
    )
    attachment = Attachment(
        url=file_info["relative_url"],
        filename=file_info["filename"],
        filesize=file_info["filesize"],
    )
    activty = AttachmentUploadActivity(created_by=agent, attachment=attachment)
    issue.add_attachment(attachment)
    issue.add_activity(activty)
    return AbilityResult(
        ability_name="write_file",
        ability_args={"file_path": file_path, "data": data},
        success=True,
        activities=[activty],
        attachments=[attachment],
    )


@ability(
    name="read_file",
    description="Read data from a specific file within the workspace, not applicable to directories",
    parameters=[
        {
            "name": "file_path",
            "description": "Path to the file. This function is applicable to files only, not directories. All file paths specified must be within the project directory.",
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
        message=data,
    )
