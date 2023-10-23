from ..registry import ability
from ..schema import AbilityResult
from ...schema import Project, Issue, Attachment
from forge.sdk import ForgeLogger

logger = ForgeLogger(__name__)


@ability(
    name="write_code",
    description=(
        "This ability allows users to write code directly into the project's workspace. "
        "IMPORTANT: Ensure you have read and understood the system architecture documented "
        "in the README.md file within the project workspace before using this ability."
    ),
    parameters=[
        {
            "name": "file_path",
            "description": "The relative path where the code will be written.",
            "type": "string",
            "required": True,
        },
        {
            "name": "code_content",
            "description": "The content of the code to be written.",
            "type": "string",
            "required": True,
        },
    ],
    output_type="object",
)
async def write_code(agent, project: Project, issue: Issue, file_path: str, code_content: str) -> AbilityResult:
    """
    Write code content to a specified file within the workspace.
    """

    # Convert the code content to bytes if it's a string
    code_content = code_content.encode() if isinstance(code_content, str) else code_content

    # Write the code content to the specified file
    file_info = agent.workspace.write_file_by_key(key=project.key, path=file_path, data=code_content)

    # Create an attachment object to store metadata about the written file
    new_attachment = Attachment(
        url=file_info.relative_url,
        filename=file_info.filename,
        filesize=file_info.filesize,
    )

    # Attach the new file to the issue and get the activity object associated with this action
    issue.add_attachment(new_attachment, agent)
    upload_activity = issue.get_last_activity()

    return AbilityResult(
        ability_name="write_code",
        ability_args={"file_path": file_path, "code_content": code_content},
        success=True,
        message="Code successfully written",
        activities=[upload_activity],
        attachments=[new_attachment],
    )


def conduct_unit_tests():
    ...


def review_code():
    ...
