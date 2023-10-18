from typing import List

from ..registry import ability
from ...schema import Workspace

from forge.sdk import ForgeLogger

logger = ForgeLogger(__name__)


@ability(
    name="list_files",
    description="List files in a workspace",
    parameters=[
        {
            "name": "path",
            "description": "Path to the workspace",
            "type": "string",
            "required": True,
        }
    ],
    output_type="list[str]",
)
async def list_files(agent, workspace: Workspace, path: str) -> List[str]:
    """
    List files in a workspace directory
    """
    return agent.workspace.list(task_id=task_id, path=str(path))


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
async def write_file(agent, workspace: Workspace, file_path: str, data: str):
    """
    Write data to a file
    """
    if isinstance(data, str):
        data = data.encode()

    agent.workspace.write(task_id=task_id, path=file_path, data=data)
    return await agent.db.create_artifact(
        task_id=task_id,
        file_name=file_path.split("/")[-1],
        relative_path=file_path,
        agent_created=True,
    )


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
async def read_file(agent, workspace: Workspace, file_path: str) -> bytes:
    """
    Read data from a file
    """
    try:
        data = agent.workspace.read(task_id=task_id, path=file_path)
    except:
        return f"Not found on path {file_path}"
    if isinstance(data, bytes):
        data = data.decode("utf-8")
    return data
