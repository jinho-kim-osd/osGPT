from ..registry import ability
from ..schema import AbilityResult
from ...schema import Project, Issue, Attachment
from forge.sdk import ForgeLogger, PromptEngine

from ...message import AIMessage, UserMessage

logger = ForgeLogger(__name__)


@ability(
    name="write_spec_sheet",
    description=(
        "Generates a spec sheet based on the provided feature specifications."
        "The detailed design from the spec sheet is stored in a README.md file within the project workspace."
    ),
    parameters=[],
    output_type="object",
)
async def write_spec_sheet(agent, project: Project, issue: Issue) -> AbilityResult:
    """
    Record the system architecture design in Markdown format in the README.md file in the workspace.
    """
    project_root = agent.workspace.get_project_path_by_key(project.key)
    file_path = project_root / "README.md"

    prompt_engine = PromptEngine("software-development")
    system_message = prompt_engine.load_prompt("write-spec-sheet-system")
    project_file_structure = agent.workspace.display_project_file_structure(project.key)
    user_message = prompt_engine.load_prompt(
        "write-spec-sheet-user",
        project=project.display(exclude=["attachments"]),
        project_file_structure=project_file_structure,
    )
    response = await agent.think(messages=[AIMessage(content=system_message), UserMessage(content=user_message)])
    architecture_content = response.content

    # Ensure the architecture content is in Markdown and write it to the README.md file
    if isinstance(architecture_content, str):
        architecture_content = architecture_content.encode()
    file_info = agent.workspace.write_file_by_key(key=project.key, path=file_path, data=architecture_content)

    new_attachment = Attachment(
        url=file_info.relative_url,
        filename=file_info.filename,
        filesize=file_info.filesize,
    )
    issue.add_attachments([new_attachment], agent)
    upload_activity = issue.get_last_activity()

    return AbilityResult(
        ability_name="write_spec_sheet",
        ability_args={},
        success=True,
        activities=[upload_activity],
        attachments=[new_attachment],
    )
