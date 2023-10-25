from forge.sdk import ForgeLogger, PromptEngine

from ..registry import ability
from ..schema import AbilityResult
from ...schema import Project, Issue, Attachment

from ...utils import parse_code_blocks
from ...message import AIMessage, UserMessage

logger = ForgeLogger(__name__)


@ability(
    name="draft_initial_code",
    description="Generates code based on the spec sheet and writes to a file.",
    parameters=[],
    output_type="object",
)
async def draft_initial_code(agent, project: Project, issue: Issue) -> AbilityResult:
    """
    Write code content to a specified file within the workspace.
    """
    spec = agent.workspace.read_by_key(project.key, path="README.md")
    spec = spec.decode("utf-8") if isinstance(spec, bytes) else spec

    prompt_engine = PromptEngine("software-development")
    system_message = prompt_engine.load_prompt("draft-code-system")
    user_message = prompt_engine.load_prompt("draft-code-user", spec=spec)
    messages = [AIMessage(content=system_message), UserMessage(content=user_message)]
    response = await agent.think(messages=messages)
    content = response.content

    code_blocks = parse_code_blocks(content)
    activities = []
    attachments = []
    for lang, path, code in code_blocks:
        # Write the code content to the specified file
        file_info = agent.workspace.write_file_by_key(key=project.key, path=path, data=code.encode())

        # Create an attachment object to store metadata about the written file
        new_attachment = Attachment(
            url=file_info.relative_url,
            filename=file_info.filename,
            filesize=file_info.filesize,
        )
        attachments.append(new_attachment)

    # Attach the new file to the issue and get the activity object associated with this action
    issue.add_attachments(attachments, agent)
    activities.append(issue.get_last_activity())

    return AbilityResult(
        ability_name="draft_initial_code",
        ability_args={},
        success=True,
        message="Code successfully written",
        activities=activities,
        attachments=attachments,
    )
