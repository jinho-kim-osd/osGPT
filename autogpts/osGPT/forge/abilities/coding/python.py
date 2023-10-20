from typing import Dict, Optional, Any
import os
import re
import ast
from contextlib import redirect_stdout, contextmanager
from io import StringIO

from pydantic import BaseModel, Field

from forge.sdk.forge_log import ForgeLogger
from ..registry import ability
from ..schema import AbilityResult
from ...schema import Project, Issue, AttachmentUploadActivity

logger = ForgeLogger(__name__)


@contextmanager
def change_cwd(path: str):
    prev_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


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
        try:
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
        except Exception as e:
            return "{}: {}".format(type(e).__name__, str(e))


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


@ability(
    name="run_python_code",
    description=(
        "A Python shell. Use this to execute python commands. "
        "Input should be a valid python command. "
        "When using this tool, sometimes output is abbreviated - "
        "make sure it does not look abbreviated before using it in your answer."
        "Note: All file paths used within the Python code should be within the specified project_root_path."
        # "Note: CSV files can be either comma-separated or tab-separated. "
        # "All csv files are tab-separated."  # TODO: should be in prompt?
    ),
    parameters=[
        {
            "name": "query",
            "description": "Code snippet to run",
            "type": "string",
            "required": True,
        },
        {
            "name": "project_root_path",
            "description": "The project root path. All file paths specified in the Python code must be within this directory.",
            "type": "string",
            "required": True,
        },
    ],
    output_type="object",
)
async def run_python_code(
    agent,
    project: Project,
    issue: Issue,
    query: str,
    project_root_path: str,
) -> AbilityResult:
    """
    Run a python code
    """
    query = sanitize_input(query)
    working_dir = agent.workspace._resolve_relative_path(".")
    python_repl = PythonAstREPLTool(
        _globals=globals(), _locals=None, _working_directory=str(working_dir)
    )

    before_attachments = set(agent.workspace.list_attachments(project_root_path))
    output = python_repl.run(query)
    after_attachments = set(agent.workspace.list_attachments(project_root_path))
    new_attachments = after_attachments - before_attachments

    activities = []
    for attachment in new_attachments:
        activty = AttachmentUploadActivity(created_by=agent, attachment=attachment)
        issue.add_attachment(attachment)
        issue.add_activity(activty)
        activities.append(activty)

    return AbilityResult(
        ability_name="read_webpage",
        ability_args={"query": query, "project_root_path": project_root_path},
        success=True,
        message=output,
        activities=activities,
        attachments=new_attachments,
    )
