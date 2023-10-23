from typing import Dict, Optional
import os
import re
import ast
from contextlib import redirect_stdout
from io import StringIO
import subprocess
import hashlib
from pathlib import Path

from pydantic import BaseModel, Field

from forge.sdk.forge_log import ForgeLogger
from ...registry import ability
from ...schema import AbilityResult
from ....utils import change_cwd
from ....schema import Project, Issue, Attachment

logger = ForgeLogger(__name__)


class PythonAstREPLTool(BaseModel):
    globals: Optional[Dict] = Field(default_factory=dict, alias="_globals")
    locals: Optional[Dict] = Field(default_factory=dict, alias="_locals")
    working_directory: Optional[str] = Field(default=None, alias="_working_directory")

    def set_working_directory(self, path: str) -> None:
        if os.path.isdir(path):
            self.working_directory = path
        else:
            print(f"Error: {path} is not a valid directory.")

    def run(
        self,
        query: str,
    ) -> str:
        """Use the tool."""
        with change_cwd(self.working_directory):
            query = sanitize_input(query)
            tree = ast.parse(query)
            module = ast.Module(tree.body[:-1], type_ignores=[])
            exec(ast.unparse(module), self.globals, self.locals)  # type: ignore
            module_end = ast.Module(tree.body[-1:], type_ignores=[])
            module_end_str = ast.unparse(module_end)  # type: ignore
            io_buffer = StringIO()
            try:
                with redirect_stdout(io_buffer):
                    ret = eval(module_end_str, self.globals, self.locals)
                    if ret is None:
                        return io_buffer.getvalue()
                    else:
                        return ret
            except Exception:
                with redirect_stdout(io_buffer):
                    exec(module_end_str, self.globals, self.locals)
                return io_buffer.getvalue()


def sanitize_input(query: str) -> str:
    """Sanitize input to the python REPL.
    Remove whitespace, backtick & python (if llm mistakes python console as terminal)

    Args:
        query: The query to sanitize

    Returns:
        str: The sanitized query
    """

    # Removes `, whitespace & python from start
    query = re.sub(r"^(\s|`)*(?i:python)?\s*", "", query)
    # Removes whitespace & ` from end
    query = re.sub(r"(\s|`)*$", "", query)
    return query


def calculate_checksum(file_path: Path) -> str:
    """
    Calculate the SHA-256 checksum of a file.

    Args:
        file_path: Path to the file.

    Returns:
        str: The SHA-256 checksum of the file.
    """
    with open(file_path, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    return file_hash


@ability(
    name="execute_python_code",
    description=(
        "Execute Python commands. Useful for manipulating existing files and data analysis. Output might be abbreviated."
    ),
    parameters=[
        {
            "name": "query",
            "description": "Code snippet to run.",
            "type": "string",
            "required": True,
        },
    ],
    output_type="object",
)
async def execute_python_code(
    agent,
    project: Project,
    issue: Issue,
    query: str,
) -> AbilityResult:
    """
    Execute a Python code snippet and attach modified or new files to the issue.
    """
    project_root = agent.workspace.get_project_path_by_key(project.key)

    # Calculating the checksums of all files before executing the code snippet
    before_checksums = {
        file: calculate_checksum(project_root / file) for file in project_root.glob("**/*") if file.is_file()
    }

    # Execute the provided Python code snippet
    try:
        query = sanitize_input(query)
        python_repl = PythonAstREPLTool(_globals=globals(), _locals=None, _working_directory=str(project_root))
        sysout = python_repl.run(query)
    except Exception as e:
        # Returning the error message in the AbilityResult
        return AbilityResult(
            ability_name="run_python_code",
            ability_args={"query": query},
            success=False,
            message=f"Error: {str(e)}",
        )

    # Calculating the checksums of all files after executing the code snippet
    after_checksums = {
        file: calculate_checksum(project_root / file) for file in project_root.glob("**/*") if file.is_file()
    }

    # Detecting new or modified files by comparing the before and after checksums
    modified_files = [file for file, checksum in after_checksums.items() if before_checksums.get(file) != checksum]

    # Attach the modified files to the issue
    activities = []
    attachments = []
    for file in modified_files:
        relative_path = agent.workspace.get_relative_path_by_key(project.key, str(file))
        new_attachment = Attachment(
            url=relative_path,
            filename=file.name,
            filesize=file.stat().st_size,
        )
        issue.add_attachment(new_attachment, agent)
        attachments.append(new_attachment)
        upload_activity = issue.get_last_activity()
        activities.append(upload_activity)

    return AbilityResult(
        ability_name="execute_python_code",
        ability_args={"query": query},
        success=True,
        message=str(sysout),
        activities=activities,
        attachments=attachments,
    )


@ability(
    name="run_python_file",
    description=(
        "Execute a specified Python file with given arguments. "
        "Provide the relative file path and a string of arguments."
    ),
    parameters=[
        {
            "name": "file_path",
            "description": "Relative path to the Python file to be executed.",
            "type": "string",
            "required": True,
        },
        {
            "name": "arguments",
            "description": "A string of arguments to be passed to the Python file during execution.",
            "type": "string",
            "required": False,
            "default": "",
        },
    ],
    output_type="object",
)
async def run_python_file(
    agent,
    project: Project,
    issue: Issue,
    file_path: str,
    arguments: Optional[str] = "",
) -> AbilityResult:
    """
    Execute a Python file with given arguments.
    """
    project_root = agent.workspace.get_project_path_by_key(project.key)
    absolute_file_path = project_root / file_path

    if not absolute_file_path.exists() or not absolute_file_path.is_file():
        return AbilityResult(
            ability_name="run_python_file",
            ability_args={"file_path": file_path, "arguments": arguments},
            success=False,
            message=f"The file '{file_path}' does not exist or is not a valid Python file.",
        )

    # Execute the Python file with the provided arguments
    try:
        command = f"python {absolute_file_path} {arguments}"
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            return AbilityResult(
                ability_name="run_python_file",
                ability_args={"file_path": file_path, "arguments": arguments},
                success=False,
                message=stderr.decode().strip(),
            )

        return AbilityResult(
            ability_name="run_python_file",
            ability_args={"file_path": file_path, "arguments": arguments},
            success=True,
            message=stdout.decode().strip(),
        )
    except Exception as e:
        return AbilityResult(
            ability_name="run_python_file",
            ability_args={"file_path": file_path, "arguments": arguments},
            success=False,
            message=str(e),
        )
