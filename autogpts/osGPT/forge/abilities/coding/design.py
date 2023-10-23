from ..registry import ability
from ..schema import AbilityResult
from ...schema import Project, Issue, Attachment, Comment
from forge.sdk import ForgeLogger

logger = ForgeLogger(__name__)


@ability(
    name="document_system_architecture",
    description=(
        "This ability is focused on crafting and documenting the system architecture in Markdown format. "
        "The design is then stored in a README.md file within the project workspace to ensure that the architecture "
        "is easily accessible and readable for all team members."
    ),
    parameters=[
        {
            "name": "architecture_content",
            "description": "The Markdown content outlining the system architecture design.",
            "type": "string",
            "required": True,
        },
    ],
    output_type="object",
)
async def document_system_architecture(
    agent, project: Project, issue: Issue, architecture_content: str
) -> AbilityResult:
    """
    Record the system architecture design in Markdown format in the README.md file in the workspace.
    """
    project_root = agent.workspace.get_project_path_by_key(project.key)
    file_path = project_root / "README.md"

    # Ensure the architecture content is in Markdown and write it to the README.md file
    if isinstance(architecture_content, str):
        architecture_content = architecture_content.encode()

    file_info = agent.workspace.write_file_by_key(key=project.key, path=file_path, data=architecture_content)

    new_attachment = Attachment(
        url=file_info.relative_url,
        filename=file_info.filename,
        filesize=file_info.filesize,
    )

    issue.add_attachment(new_attachment, agent)
    upload_activity = issue.get_last_activity()

    return AbilityResult(
        ability_name="document_system_architecture",
        ability_args={"architecture_content": architecture_content},
        success=True,
        activities=[upload_activity],
        attachments=[new_attachment],
    )
