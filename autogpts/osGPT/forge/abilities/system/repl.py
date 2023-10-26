from langchain_experimental.tools.python.tool import PythonAstREPLTool

from forge.sdk.forge_log import ForgeLogger
from ..registry import ability
from ..schema import AbilityResult
from ...utils import change_cwd, calculate_checksum
from ...schema import Project, Issue, Attachment

logger = ForgeLogger(__name__)


@ability(
    name="execute_python_code",
    description=(
        "Execute Python commands. Useful for manipulating existing files and data analysis. "
        "Use the 'print' function to display output. Output might be abbreviated."
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
        with change_cwd(project_root):
            python_repl = PythonAstREPLTool(_globals=globals(), _locals=None)
            sysout = await python_repl.arun(query)
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
    modified_files = [
        file
        for file, checksum in after_checksums.items()
        if before_checksums.get(file) != checksum and not file.name.endswith(".pyc")
    ]

    # Attach the modified files to the issue
    activities = []
    attachments = []
    for file in modified_files:
        relative_path = agent.workspace.get_relative_path_by_key(project.key, file)
        new_attachment = Attachment(
            url=relative_path,
            filename=file.name,
            filesize=file.stat().st_size,
        )
        attachments.append(new_attachment)
    issue.add_attachments(attachments, agent)
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
