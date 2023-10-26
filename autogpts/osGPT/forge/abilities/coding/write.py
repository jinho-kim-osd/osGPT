import re
import os
from forge.sdk import ForgeLogger, PromptEngine

from ..registry import ability
from ..schema import AbilityResult
from ...schema import Project, Issue, Attachment

from ...message import AIMessage, UserMessage
from ...utils import parse_code_blocks, parse_outermost_code_blocks
from .design import extract_file_structure

logger = ForgeLogger(__name__)


def extract_outer_markdown(text: str) -> str:
    """
    Extracts the outermost markdown block from the given text.
    Assumes that the outer markdown block is surrounded by ```markdown ... ```.
    """
    pattern = r"```markdown\b(.*?)(?=```markdown\b|```$)"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1) if match else ""


@ability(
    name="write_code",
    description="Writes code for the selected task based on the design.",
    parameters=[
        {
            "name": "file_path",
            "description": "Path to the code file to write.",
            "type": "string",
            "required": True,
        },
        {
            "name": "design_document_path",
            "description": "Path to the design document used as reference. By default, this refers to the './README.md' file.",
            "type": "string",
            "required": True,
            "default": "./README.md",
        },
        {
            "name": "error_message",
            "description": "An optional error message if there was an issue with writing the code.",
            "type": "string",
            "required": False,
            "default": "",
        },
    ],
    output_type="object",
)
async def write_code(
    agent,
    project: Project,
    issue: Issue,
    file_path: str,
    design_document_path: str = "./README.md",
    error_message: str = "",
) -> AbilityResult:
    # Use design_document as a reference to write code
    design_document = agent.workspace.read_by_key(project.key, path=design_document_path)
    design_document = design_document.decode("utf-8")

    try:
        original_code = agent.workspace.read_by_key(key=project.key, path=file_path)
        original_code = original_code.decode("utf-8")
    except:
        original_code = ""

    prompt_engine = PromptEngine("software-development")
    system_message = prompt_engine.load_prompt("write-code-system")
    user_message = prompt_engine.load_prompt(
        "write-code-user", original_code=original_code, error_message=error_message, design_document=design_document
    )
    messages = [AIMessage(content=system_message), UserMessage(content=user_message)]
    response = await agent.think(messages=messages)
    print(response.content)
    messages.append(response)

    code_blocks = parse_code_blocks(response.content)

    attachments = []
    for lang, file_path, code in code_blocks:
        file_info = agent.workspace.write_file_by_key(project.key, file_path, code.encode())
        code_attachment = Attachment(
            url=file_info.relative_url,
            filename=file_info.filename,
            filesize=file_info.filesize,
        )
        user_message = prompt_engine.load_prompt(
            "update-design-document-system", original_code=code, design_document=design_document
        )
        messages.append(UserMessage(content=user_message))
        design_response = await agent.think(messages=messages)
        print(design_response.content)
        design_document = extract_outer_markdown(design_response.content)
        design_file_info = agent.workspace.write_file_by_key(
            project.key, design_document_path, design_document.encode()
        )
        design_file_attachment = Attachment(
            url=design_file_info.relative_url,
            filename=design_file_info.filename,
            filesize=design_file_info.filesize,
        )
        attachments.append(code_attachment)
        attachments.append(design_file_attachment)

    issue.add_attachments(attachments, agent)
    upload_activity = issue.get_last_activity()

    return AbilityResult(
        ability_name="write_code",
        ability_args={"file_path": file_path, "design_document": design_document},
        message=extract_file_structure(design_document),
        success=True,
        activities=[upload_activity],
        attachments=attachments,
    )


@ability(
    name="write_unit_tests",
    description="Write unit tests based on the design for the provided Python code file. The generated test file will be named as 'test_<filename>.py'.",
    parameters=[
        {
            "name": "code_file_path",
            "description": "Path to the Python code file for which unit tests should be generated.",
            "type": "string",
            "required": True,
        },
        {
            "name": "design_document_path",
            "description": "Path to the design document used as reference. By default, this refers to the './README.md' file.",
            "type": "string",
            "required": True,
            "default": "./README.md",
        },
    ],
    output_type="object",
)
async def write_unit_tests(
    agent, project: Project, issue: Issue, code_file_path: str, design_document_path: str = "./README.md"
) -> AbilityResult:
    # Use design_document as a reference to write code
    design_document = agent.workspace.read_by_key(project.key, path=design_document_path)
    design_document = design_document.decode("utf-8")

    # Extracting filename without extension to append 'test_*.py'
    code = agent.workspace.read_by_key(key=project.key, path=code_file_path)
    code = code.decode("utf-8")

    prompt_engine = PromptEngine("software-development")
    system_message = prompt_engine.load_prompt("write-unit-tests-system")
    user_message = prompt_engine.load_prompt("write-unit-tests-user", code=code, design_document=design_document)
    messages = [AIMessage(content=system_message), UserMessage(content=user_message)]
    code_response = await agent.think(messages=messages)
    print(code_response.content)
    messages.append(code_response)

    code_blocks = extract_outer_markdown(code_response.content)

    attachments = []
    for lang, file_path, unit_test_code in code_blocks:
        unit_test_file_info = agent.workspace.write_file_by_key(project.key, file_path, unit_test_code.encode())
        unit_test_code_attachment = Attachment(
            url=unit_test_file_info.relative_url,
            filename=unit_test_file_info.filename,
            filesize=unit_test_file_info.filesize,
        )
        user_message = prompt_engine.load_prompt(
            "update-design-document-system", code=code, design_document=design_document
        )
        messages.append(UserMessage(content=user_message))
        design_response = await agent.think(messages=messages)
        print(design_response.content)
        design_document = extract_outer_markdown(design_response.content)[0]
        design_file_info = agent.workspace.write_file_by_key(
            project.key, design_document_path, design_document.encode()
        )
        design_file_attachment = Attachment(
            url=design_file_info.relative_url,
            filename=design_file_info.filename,
            filesize=design_file_info.filesize,
        )
        attachments.append(unit_test_code_attachment)
        attachments.append(design_file_attachment)

    issue.add_attachments(attachments, agent)
    upload_activity = issue.get_last_activity()

    return AbilityResult(
        ability_name="generate_unit_tests",
        ability_args={"code_file_path": code_file_path, "design_document_path": design_document_path},
        message=extract_file_structure(design_document),
        success=True,
        activities=[upload_activity],
        attachments=attachments,
    )
