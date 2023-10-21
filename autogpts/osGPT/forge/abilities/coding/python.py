from typing import Dict, Optional
import os
import re
import ast
from contextlib import redirect_stdout, contextmanager
from io import StringIO

from pydantic import BaseModel, Field

from forge.sdk.forge_log import ForgeLogger
from ..registry import ability
from ..schema import AbilityResult
from ...schema import Project, Issue, Attachment, AttachmentUploadActivity

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


@ability(
    name="run_python_code",
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
async def run_python_code(
    agent,
    project: Project,
    issue: Issue,
    query: str,
) -> AbilityResult:
    """
    Run a python code
    """
    query = sanitize_input(query)
    project_root = agent.workspace.get_project_path_by_key(project.key)
    python_repl = PythonAstREPLTool(
        _globals=globals(), _locals=None, _working_directory=str(project_root)
    )

    # TODO: find better approach
    before_file_infos = agent.workspace.list_files_by_key(project.key)
    output = python_repl.run(query)
    after_file_infos = agent.workspace.list_files_by_key(project.key)

    new_or_modified_files = []
    for after_file_info in after_file_infos:
        is_new = True
        for before_file_info in before_file_infos:
            if before_file_info["filename"] == after_file_info["filename"]:
                is_new = False
                if (
                    before_file_info["updated_at"] != after_file_info["updated_at"]
                    or before_file_info["filesize"] != after_file_info["filesize"]
                ):
                    new_or_modified_files.append(
                        {"file_info": after_file_info, "status": "modified"}
                    )
                break
        if is_new:
            new_or_modified_files.append(
                {"file_info": after_file_info, "status": "new"}
            )

    activities = []
    attachments = []
    for file in new_or_modified_files:
        file_info = file["file_info"]
        new_attachment = Attachment(
            url=file_info["relative_url"],
            filename=file_info["filename"],
            filesize=file_info["filesize"],
        )

        if file["status"] == "modified":
            for old_attachment in issue.attachments:
                if old_attachment.filename == new_attachment.filename:
                    issue.remove_attachment(old_attachment)
                    break

        activty = AttachmentUploadActivity(created_by=agent, attachment=new_attachment)
        issue.add_attachment(new_attachment)
        issue.add_activity(activty)

        attachments.append(new_attachment)
        activities.append(activty)

    return AbilityResult(
        ability_name="run_python_code",
        ability_args={"query": query},
        success=True,
        message=str(output),
        activities=activities,
        attachments=attachments,
    )
