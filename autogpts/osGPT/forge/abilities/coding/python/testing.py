from typing import Optional, List, Union
import os
import json
import asyncio
import platform
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO

from pydantic import BaseModel, Field

from forge.sdk.forge_log import ForgeLogger
from ...registry import ability
from ...schema import AbilityResult
from ....utils import change_cwd
from ....schema import Project, Issue

logger = ForgeLogger(__name__)

class ShellTool(BaseModel):
    working_directory: Optional[str] = Field(default=None)

    def set_working_directory(self, path: str) -> None:
        if os.path.isdir(path):
            self.working_directory = path
        else:
            print(f"Error: {path} is not a valid directory.")

    async def run(
        self,
        commands: Union[str, List[str]]
    ) -> str:
        """Use the tool."""
        if isinstance(commands, str):
            commands = [commands]

        output = StringIO()
        errors = StringIO()

        with change_cwd(self.working_directory):
            for command in commands:
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                with redirect_stdout(output), redirect_stderr(errors):
                    await process.communicate()

        return output.getvalue(), errors.getvalue()

def _get_platform() -> str:
    """Get platform."""
    system = platform.system()
    if system == "Darwin":
        return "MacOS"
    return system



@ability(
    name="test_python_file",
    description=(
        "This ability allows you to execute Python test scripts directly from the shell environment on your "
        f"{_get_platform()} machine. Simply provide the file path of the Python script you want to execute. "
        "You can also include additional shell commands to be executed before running the Python script, if necessary."
    ),
    parameters=[
        {
            "name": "test_file_path",
            "description": "The file path to the Python test script.",
            "type": "string",
            "required": True,
        },
        {
            "name": "additional_commands",
            "description": "Additional shell commands to execute before running the test, if necessary. Deserialized using json.loads",
            "type": "string",
            "required": False,
        }
    ],
    output_type="object",
)
async def test_python_file(
    agent,
    project: Project,
    issue: Issue,
    test_file_path: str,
    additional_commands: Union[str, List[str]] = None,
) -> AbilityResult:
    """
    Run shell commands
    """
    project_root = agent.workspace.get_project_path_by_key(project.key)
    shell_tool = ShellTool(working_directory=str(project_root))

     # Prepare the commands
    commands = []
    if additional_commands:
        additional_commands = json.loads(additional_commands)
        commands.extend(additional_commands)
    commands.append(f"python {test_file_path}")

    output, errors = await shell_tool.run(commands)

    return AbilityResult(
        ability_name="test_python_file",
        ability_args={"test_file_path": test_file_path, "additional_commands": additional_commands},
        success=errors == "",
        message=output if errors == "" else errors
    )