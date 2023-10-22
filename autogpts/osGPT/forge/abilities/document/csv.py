import pandas as pd
import json

from ..registry import ability
from ..schema import AbilityResult
from ...schema import Project, Issue, Attachment, AttachmentUploadActivity
from ..coding.execute import sanitize_input, PythonAstREPLTool


@ability(
    name="read_csv",
    description="Read data from a CSV file.",
    parameters=[
        {
            "name": "file_path",
            "description": "Path to the CSV file to read data from",
            "type": "string",
            "required": True,
        },
        {
            "name": "separator",
            "description": "The separator used in the CSV file. Default is comma ','.",
            "type": "string",
            "required": False,
            "default": ",",
        },
    ],
    output_type="string",
)
async def read_csv(
    agent, project: Project, issue: Issue, file_path: str, separator: str = ","
) -> AbilityResult:
    """
    Read data from a CSV file
    """
    project_root = agent.workspace.get_project_path_by_key(project.key)
    full_path = project_root / file_path

    df = pd.read_csv(full_path, sep=separator)
    data = df.head(200).to_string()  # Adjust the number of rows to display here

    # Truncate the string if it's too long
    max_length = 2000
    if len(data) > max_length:
        truncated_data = data[:max_length] + "...[abbreviated]"
    else:
        truncated_data = data

    return AbilityResult(
        ability_name="read_csv",
        ability_args={"file_path": file_path, "separator": separator},
        success=True,
        message=json.dumps(truncated_data) if data is not None else None,
    )


@ability(
    name="detect_csv_separator",
    description=(
        "Detect the separator used in a given CSV file. This tool identifies whether "
        "a comma ',' or a tab '\\t' is used as the separator in the CSV file. "
        "Provide the path to the CSV file as input."
    ),
    parameters=[
        {
            "name": "file_path",
            "description": "Relative path to the CSV file",
            "type": "string",
            "required": True,
        },
    ],
    output_type="object",
)
async def detect_csv_separator(
    agent,
    project: Project,
    issue: Issue,
    file_path: str,
) -> AbilityResult:
    """
    Detect the separator used in the CSV file
    """
    separator = None
    project_root = agent.workspace.get_project_path_by_key(project.key)
    full_path = project_root / file_path
    with open(full_path, "r") as file:
        first_line = file.readline()
        print(first_line)
        if "," in first_line:
            separator = ","
        elif "\t" in first_line:
            separator = "\\t"

    if separator:
        message = f"The separator used in the file is: {separator}"
        success = True
    else:
        message = "Unable to detect the separator used in the file."
        success = False

    return AbilityResult(
        ability_name="detect_csv_separator",
        ability_args={"file_path": file_path},
        success=success,
        message=message,
    )


@ability(
    name="csv_python_executor",
    description=(
        "Execute Python code for a specific CSV file using pandas. "
        "The DataFrame is automatically initialized with 'df = pd.read_csv(<provided_file_path>, sep=<provided_sep>)'. "
        "Simply add the necessary operations following this to perform your desired analysis or modifications on the data. "
        "You can view the output by printing to the console, e.g., print(df['col1'].sum())."
    ),
    parameters=[
        {
            "name": "file_path",
            "description": "Path to the CSV file to be manipulated.",
            "type": "string",
            "required": True,
        },
        {
            "name": "separator",
            "description": "The separator used in the CSV file. Default is comma ','.",
            "type": "string",
            "required": False,
            "default": ",",
        },
        {
            "name": "python_code",
            "description": ("Python code to execute on the specified CSV file. "),
            "type": "string",
            "required": True,
        },
    ],
    output_type="object",
)
async def csv_python_executor(
    agent,
    project: Project,
    issue: Issue,
    file_path: str,
    separator: str = ",",
    python_code: str = "",
) -> AbilityResult:
    """
    Run a python code
    """
    project_dir = agent.workspace.get_project_path_by_key(project.key)
    if "pd.read_csv" not in python_code:
        python_code = (
            f"df = pd.read_csv('{file_path}', sep='{separator}')\n{python_code}"
        )
    else:
        python_code = python_code.replace("CSV_FILE_PATH", f"{project_dir}/{file_path}")
    python_code = sanitize_input(python_code)
    python_repl = PythonAstREPLTool(
        _globals=globals(), _locals=None, _working_directory=str(project_dir)
    )

    # TODO: find better approach
    before_file_infos = agent.workspace.list_files_by_key(project.key)
    output = python_repl.run(python_code)
    after_file_infos = agent.workspace.list_files_by_key(project.key)

    new_or_modified_files = []
    for after_file_info in after_file_infos:
        is_new = True
        for before_file_info in before_file_infos:
            if before_file_info["filename"] == after_file_info["filename"]:
                is_new = False
                if (
                    before_file_info["updated_at"] != after_file_info["updated_at"]
                    or before_file_info["filesize"] != after_file_info["filesize"]
                ):
                    new_or_modified_files.append(
                        {"file_info": after_file_info, "status": "modified"}
                    )
                break
        if is_new:
            new_or_modified_files.append(
                {"file_info": after_file_info, "status": "new"}
            )

    activities = []
    attachments = []
    for file in new_or_modified_files:
        file_info = file["file_info"]
        new_attachment = Attachment(
            url=file_info["relative_url"],
            filename=file_info["filename"],
            filesize=file_info["filesize"],
        )

        if file["status"] == "modified":
            for old_attachment in issue.attachments:
                if old_attachment.filename == new_attachment.filename:
                    issue.remove_attachment(old_attachment)
                    break

        activty = AttachmentUploadActivity(created_by=agent, attachment=new_attachment)
        issue.add_attachment(new_attachment)
        issue.add_activity(activty)

        attachments.append(new_attachment)
        activities.append(activty)

    return AbilityResult(
        ability_name="csv_python_executor",
        ability_args={"python_code": python_code},
        success=True,
        message=str(output),
        activities=activities,
        attachments=attachments,
    )
