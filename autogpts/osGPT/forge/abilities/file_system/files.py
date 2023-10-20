from typing import List

from ..registry import ability
from ...schema import Project, Issue, Attachment, AttachmentUploadActivity
from forge.sdk import ForgeLogger

logger = ForgeLogger(__name__)


# @ability(
#     name="list_files",
#     description="List files in a workspace",
#     parameters=[
#         {
#             "name": "path",
#             "description": "Path to the workspace",
#             "type": "string",
#             "required": True,
#         }
#     ],
#     output_type="list[str]",
# )
# async def list_files(agent, project: Project, issue: Issue, path: str) -> List[str]:
#     """
#     List files in a workspace directory
#     """
#     return agent.workspace.list_relative_path(path)


@ability(
    name="write_file",
    description="Write data to a file",
    parameters=[
        {
            "name": "file_path",
            "description": "Path to the file",
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
) -> AttachmentUploadActivity:
    """
    Write data to a file
    """
    if isinstance(data, str):
        data = data.encode()

    attachment = agent.workspace.write_relative_path(path=file_path, data=data)
    activty = AttachmentUploadActivity(created_by=agent, attachment=attachment)
    issue.add_attachment(attachment)
    issue.add_activity(activty)
    return activty


@ability(
    name="read_file",
    description="Read data from a workspace",
    parameters=[
        {
            "name": "file_path",
            "description": "Path to the file",
            "type": "string",
            "required": True,
        },
    ],
    output_type="bytes",
)
async def read_file(agent, project: Project, issue: Issue, file_path: str) -> bytes:
    """
    Read data from a file
    """
    try:
        data = agent.workspace.read_relative_path(path=file_path)
    except:
        return f"Not found on path {file_path}"
    if isinstance(data, bytes):
        data = data.decode("utf-8")
    return data
