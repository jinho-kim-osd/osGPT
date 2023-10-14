"""
Ability for running Python code
"""

from typing import Dict, Optional
import os
import re
import ast
from contextlib import redirect_stdout, contextmanager
from io import StringIO

from pydantic import BaseModel, Field

from ...forge_log import ForgeLogger
from ..registry import ability

logger = ForgeLogger(__name__)

MAX_TRIM_OUTPUT = 300


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
    ),
    parameters=[
        {
            "name": "query",
            "description": "Code snippet to run",
            "type": "string",
            "required": True,
        }
    ],
    output_type="dict[str, Any]",
)
async def run_python_code(agent, task_id: str, query: str) -> str:
    """
    Run a python code
    """
    query = sanitize_input(query)
    working_dir = agent.workspace._resolve_path(task_id, ".")
    python_repl = PythonAstREPLTool(
        _globals=globals(), _locals=None, _working_directory=str(working_dir)
    )
    before_files = set(os.listdir(working_dir))
    output = python_repl.run(query)
    if len(output) > MAX_TRIM_OUTPUT:
        output = output[: MAX_TRIM_OUTPUT - 3] + "[...]"

    after_files = set(os.listdir(working_dir))

    new_files = after_files - before_files

    artifacts = []
    for file_name in new_files:
        logger.info(f"Artifact created: {file_name}")
        file_path = working_dir / file_name
        artifact = await agent.db.create_artifact(
            task_id=task_id,
            file_name=str(file_path).split("/")[-1],
            relative_path="",
            agent_created=True,
        )
        artifacts.append(artifact)
    return {"stdout": output, "new_files": new_files, "artifacts": artifacts}
