import json

from langchain.tools.shell import ShellTool

from forge.sdk.forge_log import ForgeLogger
from ..registry import ability
from ..schema import AbilityResult
from ...utils import change_cwd, calculate_checksum
from ...schema import Project, Issue, Attachment

logger = ForgeLogger(__name__)


@ability(
    name="execute_shell_commands",
    description=(
        "Execute shell commands. Useful for file manipulations, data processing, and system interactions."
        " Be aware that the output might be abbreviated."
    ),
    parameters=[
        {
            "name": "commands",
            "description": "a shell commands to execute.",
            "type": "string",
            "required": True,
        },
    ],
    output_type="object",
)
async def execute_shell_commands(
    agent,
    project: Project,
    issue: Issue,
    commands: str,
) -> AbilityResult:
    """
    Execute a list of shell commands and attach modified or new files to the issue.
    """
    project_root = agent.workspace.get_project_path_by_key(project.key)

    # Calculating the checksums of all files before executing the shell commands
    before_checksums = {
        file: calculate_checksum(project_root / file) for file in project_root.glob("**/*") if file.is_file()
    }

    # Execute the provided shell commands
    try:
        with change_cwd(project_root):
            shell = ShellTool(_globals=globals(), _locals=None)
            sysout = await shell.arun({"commands": [commands]})
    except Exception as e:
        # Returning the error message in the AbilityResult
        return AbilityResult(
            ability_name="execute_shell_commands",
            ability_args={"commands": commands},
            success=False,
            message=f"Error: {str(e)}",
        )

    # Calculating the checksums of all files after executing the shell commands
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
        ability_name="execute_shell_commands",
        ability_args={"commands": commands},
        success=True,
        message=str(sysout),
        activities=activities,
        attachments=attachments,
    )
