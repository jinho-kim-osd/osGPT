from forge.sdk import ForgeLogger, PromptEngine

from ..registry import ability
from ..schema import AbilityResult
from ...schema import Project, Issue, Attachment

from ...message import AIMessage, UserMessage

logger = ForgeLogger(__name__)


import re


def apply_changes_to_original(original_text: str, edit_text: str) -> str:
    """
    Given the original text and the edit blocks, apply the changes
    specified in the edit blocks to the original text.

    :param original_text: The original text or code.
    :param edit_text: The edit blocks containing the changes.
    :return: The updated text after applying the edits.
    """
    # Parsing the edit blocks
    edit_blocks = re.findall(r"<<<<<<< HEAD\n(.*?)=======\n(.*?)>>>>>>> updated", edit_text, re.DOTALL)

    updated_text = original_text
    for before, after in edit_blocks:
        before = before.strip()
        after = after.strip()

        if before in updated_text:
            updated_text = updated_text.replace(before, after)
        else:
            # Handling the scenario when the code block to be replaced is not found.
            logger.warn(f"Code block not found:\n{before}\n")

    return updated_text


@ability(
    name="review_and_update_code",
    description=(
        "This ability allows users to review and update the code in the project's workspace based on feedback. "
    ),
    parameters=[
        {
            "name": "file_path",
            "description": "The relative path where the code will be written.",
            "type": "string",
            "required": True,
        },
    ],
    output_type="object",
)
async def review_and_update_code(agent, project: Project, issue: Issue, file_path: str) -> AbilityResult:
    """
    Review and update the code in a specified file based on the feedback.
    """
    spec = agent.workspace.read_by_key(project.key, path="README.md")
    spec = spec.decode("utf-8") if isinstance(spec, bytes) else spec

    # Read the current code content.
    original_code = agent.workspace.read_by_key(key=project.key, path=file_path)
    original_code = original_code.decode("utf-8") if isinstance(original_code, bytes) else original_code

    prompt_engine = PromptEngine("software-development")
    system_message = prompt_engine.load_prompt("review-code-system")
    user_message = prompt_engine.load_prompt("review-code-user", code=original_code, spec=spec)
    response = await agent.think(messages=[AIMessage(content=system_message), UserMessage(content=user_message)])
    edit_code = response.content
    print(edit_code)

    new_code = apply_changes_to_original(original_code, edit_code)

    activities = []
    attachments = []
    if new_code == original_code:
        message = "Code reviewed and found to be in compliance with the specifications. No changes needed."
    else:
        # Write the updated code content back to the specified file
        new_code_content = new_code.encode() if isinstance(new_code, str) else new_code
        file_info = agent.workspace.write_file_by_key(key=project.key, path=file_path, data=new_code_content)

        # Create an attachment object to store metadata about the updated file
        updated_attachment = Attachment(
            url=file_info.relative_url,
            filename=file_info.filename,
            filesize=file_info.filesize,
        )

        # Attach the updated file to the issue and get the activity object associated with this action
        issue.add_attachments([updated_attachment], agent)
        attachments.append(updated_attachment)
        upload_activity = issue.get_last_activity()
        activities.append(upload_activity)
        message = f"Code reviewed and necessary changes have been made.\nEdited:\n{edit_code}"
    return AbilityResult(
        ability_name="review_and_update_code",
        ability_args={"file_path": file_path},
        success=True,
        message=message,
        activities=activities,
        attachments=attachments,
    )
