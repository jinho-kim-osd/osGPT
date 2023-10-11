"""
Ability for running Python code
"""
from typing import Dict, Optional
import os
import re
import multiprocessing
import sys
from io import StringIO

from pydantic import BaseModel, Field

from ...forge_log import ForgeLogger
from ..registry import ability

logger = ForgeLogger(__name__)


class PythonREPL(BaseModel):
    """Simulates a standalone Python REPL."""

    globals: Optional[Dict] = Field(default_factory=dict, alias="_globals")
    locals: Optional[Dict] = Field(default_factory=dict, alias="_locals")
    working_directory: Optional[str] = Field(default=None, alias="_working_directory")

    @classmethod
    def worker(
        cls,
        command: str,
        globals: Optional[Dict],
        locals: Optional[Dict],
        queue: multiprocessing.Queue,
    ) -> None:
        old_stdout = sys.stdout
        sys.stdout = mystdout = StringIO()
        try:
            exec(command, globals, locals)
            sys.stdout = old_stdout
            queue.put(mystdout.getvalue())
        except Exception as e:
            sys.stdout = old_stdout
            queue.put(repr(e))

    def set_working_directory(self, path: str) -> None:
        if os.path.isdir(path):
            self.working_directory = path
        else:
            print(f"Error: {path} is not a valid directory.")

    def run(self, command: str, timeout: Optional[int] = None) -> str:
        """Run command with own globals/locals and returns anything printed.
        Timeout after the specified number of seconds."""
        if self.working_directory:
            os.chdir(self.working_directory)

        queue: multiprocessing.Queue = multiprocessing.Queue()

        # Only use multiprocessing if we are enforcing a timeout
        if timeout is not None:
            # create a Process
            p = multiprocessing.Process(
                target=self.worker, args=(command, self.globals, self.locals, queue)
            )
            p.start()

            # wait for the process to finish or kill it after timeout seconds
            p.join(timeout)

            if p.is_alive():
                p.terminate()
                return "Execution timed out"
        else:
            self.worker(command, self.globals, self.locals, queue)
        # get the result from the worker function
        return queue.get()


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
    description="Executes Python code. Output is captured and returned via print statements.",
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
    working_dir = agent.workspace._resolve_path(task_id, "/")
    working_dir.mkdir(exist_ok=True)

    python_repl = PythonREPL(
        _globals=globals(), _locals=None, _working_directory=str(working_dir)
    )
    before_files = set(os.listdir(working_dir))
    output = python_repl.run(query)
    after_files = set(os.listdir(working_dir))

    new_files = after_files - before_files
    logger.info(f"{str(after_files)} - {str(before_files)}")
    artifacts = []
    for file_name in new_files:
        file_path = working_dir / file_name
        artifact = await agent.db.create_artifact(
            task_id=task_id,
            file_name=str(file_path).split("/")[-1],
            relative_path="",
            agent_created=True,
        )
        artifacts.append(artifact)
    return {"stdout": output, "artifacts": artifacts}
