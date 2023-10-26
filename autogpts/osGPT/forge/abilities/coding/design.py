from typing import Optional
import re
import os

from ..registry import ability
from ..schema import AbilityResult
from ...schema import Project, Issue, Attachment
from forge.sdk import ForgeLogger, PromptEngine

from ...message import AIMessage, UserMessage

logger = ForgeLogger(__name__)


def extract_file_structure(design_document: str) -> str:
    pattern = r"## File Structure\n(.*?)(?=## Interface)"
    match = re.search(pattern, design_document, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def create_missing_files_from_structure(extracted_structure: str, root_path: str):
    # Extract all file and directory paths
    paths = re.findall(r"├── (.+?)(?=\s*\()", extracted_structure)  # Adjusted to stop at parentheses

    # Iterate over each path and create it if not exists
    for path in paths:
        full_path = os.path.join(root_path, path)

        # It's a file (based on your provided structure)
        if not os.path.exists(full_path):
            with open(full_path, "w") as f:
                f.write("")  # Creating an empty file


@ability(
    name="design_solution",
    description="Designs the solution architecture or approach for a given task and records it in the README.md file.",
    parameters=[
        {
            "name": "existing_design_file",
            "description": "Path to the existing design document file.",
            "type": "string",
            "required": False,
        }
    ],
    output_type="object",
)
async def design_solution(
    agent, project: Project, issue: Issue, existing_design_file: Optional[str] = None
) -> AbilityResult:
    """
    Record the system architecture design in Markdown format in the README.md file in the workspace.
    """

    try:
        design_document = agent.workspace.read_by_key(project.key, existing_design_file)
    except:
        project_root = agent.workspace.get_project_path_by_key(project.key)
        file_path = project_root / "README.md"
        design_document = ""
        agent.workspace.write_file_by_key(key=project.key, path=file_path, data=design_document.encode())

    prompt_engine = PromptEngine("software-development")
    system_message = prompt_engine.load_prompt("design-solution-system")
    file_structure = agent.workspace.display_project_file_structure(project.key)
    user_message = prompt_engine.load_prompt(
        "design-solution-user",
        requirements=issue.summary,
        design_document=design_document,
        file_structure=file_structure,
    )
    response = await agent.think(messages=[AIMessage(content=system_message), UserMessage(content=user_message)])
    design_document = response.content

    extracted_structure = extract_file_structure(design_document)
    root_path = agent.workspace.get_project_path_by_key(project.key)
    create_missing_files_from_structure(extracted_structure, root_path)

    # Ensure the architecture content is in Markdown and write it to the README.md file
    file_info = agent.workspace.write_file_by_key(key=project.key, path=file_path, data=design_document.encode())

    new_attachment = Attachment(
        url=file_info.relative_url,
        filename=file_info.filename,
        filesize=file_info.filesize,
    )
    issue.add_attachments([new_attachment], agent)
    upload_activity = issue.get_last_activity()

    return AbilityResult(
        ability_name="design_solution",
        ability_args={"existing_design_file": existing_design_file or ""},
        message=extracted_structure,
        success=True,
        activities=[upload_activity],
        attachments=[new_attachment],
    )
