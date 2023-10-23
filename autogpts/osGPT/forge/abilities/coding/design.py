import json
from ..registry import ability
from ..schema import AbilityResult
from ...schema import Project, Issue, Attachment, Comment
from forge.sdk import ForgeLogger

logger = ForgeLogger(__name__)


@ability(
    name="design_system_architecture",
    description=(
        "Before starting code development, it's mandatory to create a system architecture design and "
        "document it in a README.md file in the workspace. This ability facilitates the documentation of the "
        "architecture design."
    ),
    parameters=[
        {
            "name": "architecture_content",
            "description": "Content of the system architecture design.",
            "type": "string",
            "required": True,
        },
    ],
    output_type="object",
)
async def design_system_architecture(agent, project: Project, issue: Issue, architecture_content: str) -> AbilityResult:
    """
    Create a system architecture design and document it in a README.md file.
    """
    project_root = agent.workspace.get_project_path_by_key(project.key)
    file_path = project_root / "README.md"

    # Write the architecture content to the README.md file
    if isinstance(architecture_content, str):
        architecture_content = architecture_content.encode()

    file_info = agent.workspace.write_file_by_key(key=project.key, path=file_path, data=architecture_content)

    new_attachment = Attachment(
        url=file_info.relative_url,
        filename=file_info.filename,
        filesize=file_info.filesize,
    )

    # Add a comment indicating that the system architecture design is documented in the README.md file
    comment = Comment(
        created_by=agent,
        content=f"System architecture design has been documented in 'README.md'.",
        attachments=[new_attachment],
    )
    issue.add_activity(comment)
    issue.add_attachment(new_attachment, agent)
    upload_activity = issue.get_last_activity()

    return AbilityResult(
        ability_name="design_system_architecture",
        ability_args={"architecture_content": architecture_content},
        success=True,
        activities=[upload_activity, comment],
        attachments=[new_attachment],
    )


@ability(
    name="read_system_architecture",
    description="Read the system architecture design from the README.md file in the workspace.",
    parameters=[
        {
            "name": "file_path",
            "description": "Path to the file.",
            "type": "string",
            "required": True,
        },
    ],
    output_type="string",
)
async def read_system_architecture(agent, project: Project, issue: Issue, file_path: str) -> AbilityResult:
    """
    Read the system architecture design documented in the README.md file.
    """
    data = agent.workspace.read_by_key(key=project.key, path=file_path)
    if isinstance(data, bytes):
        data = data.decode("utf-8")
    return AbilityResult(
        ability_name="read_file",
        ability_args={"file_path": file_path},
        success=True,
        message=json.dumps(data),
    )
