"""
Ability for running Python code
"""
from typing import Dict, Optional
import subprocess
import json
import os
import re
import multiprocessing
import sys
from io import StringIO

from pydantic import BaseModel, Field

# from ...forge_log import ForgeLogger
# from ..registry import ability

# logger = ForgeLogger(__name__)


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


async def run_python_file(agent, task_id: str, file_name: str) -> Dict:
    """
    run_python_file
    Uses the UNSAFE exec method after reading file from local workspace
    Look for safer method
    """

    get_cwd = agent.workspace.get_cwd_path(task_id)

    return_dict = {"return_code": -1, "stdout": "", "stderr": ""}

    command = f"python {file_name}"

    try:
        req = subprocess.run(command, shell=True, capture_output=True, cwd=get_cwd)

        return_dict["return_code"] = req.returncode
        return_dict["stdout"] = req.stdout.decode()
        return_dict["stderr"] = req.stderr.decode()
    except Exception as err:
        # logger.error(f"subprocess call failed: {err}")
        raise err

    try:
        return_json = json.dumps(return_dict)
    except json.JSONDecodeError as err:
        # logger.error(f"JSON dumps failed: {err}")
        raise err
    return return_json


def run_python_code(agent, task_id: str, query: str) -> Dict:
    """
    Run a python code
    """
    query = sanitize_input(query)
    # base_path = agent.workspace.base_path
    python_repl = PythonREPL(
        _globals=globals(),
        _locals=None,  # _working_directory=base_path
    )
    return python_repl.run(query)


if __name__ == "__main__":
    code = """
import pandas as pd; 
from io import BytesIO; 
df = pd.read_csv(BytesIO(b'id,name,timestamp\\n3,Alice,2023-09-25 14:10:00\\n1,Bob,2023-09-24 12:05:00\\n2,Charlie,2023-09-24 12:10:00\\n4,David,2023-09-26 16:20:00\\n')); 
sorted_df = df.sort_values('timestamp'); 
sorted_df.to_csv("output.csv", index=False)
print(sorted_df)
    """
    print(run_python_code("gel", "ge", code))
    print(os.getcwd())
