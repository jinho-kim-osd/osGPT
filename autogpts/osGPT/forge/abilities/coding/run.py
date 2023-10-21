import subprocess
import json
from ..registry import ability
from ..schema import AbilityResult
from ...schema import Project, Issue
from forge.sdk import ForgeLogger

logger = ForgeLogger(__name__)


@ability(
    name="execute_python_file",
    description="Execute a specified Python file within the workspace and return the output.",
    parameters=[
        {
            "name": "file_path",
            "description": "Path to the Python file to be executed.",
            "type": "string",
            "required": True,
        }
    ],
    output_type="object",
)
async def execute_python_file(
    agent, project: Project, issue: Issue, file_path: str
) -> AbilityResult:
    """
    Execute specified Python file and return the output
    """
    project_root = agent.workspace.get_project_path_by_key(project.key)
    full_file_path = project_root / file_path

    try:
        # Ensure this execution mechanism adheres to your security protocols
        completed_process = subprocess.run(
            ["python", full_file_path], check=True, text=True, capture_output=True
        )
        output = completed_process.stdout.strip()

    except subprocess.CalledProcessError as e:
        logger.error(f"Error occurred while executing the Python file: {e}")
        return AbilityResult(
            ability_name="execute_python_file",
            ability_args={"file_path": file_path},
            success=False,
            message="Error occurred while executing the Python file.",
        )

    return AbilityResult(
        ability_name="execute_python_file",
        ability_args={"file_path": file_path},
        success=True,
        message=output,
    )
