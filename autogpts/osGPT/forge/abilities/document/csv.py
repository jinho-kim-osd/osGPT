import pandas as pd
import json

from ..registry import ability
from ..schema import AbilityResult
from ...schema import Project, Issue


@ability(
    name="read_csv",
    description=(
        "Read a specified number of rows from a CSV file and return them as a string. "
        "Useful for quickly inspecting the structure and content of the file. "
    ),
    parameters=[
        {
            "name": "file_path",
            "description": "The relative path to the CSV file.",
            "type": "string",
            "required": True,
        },
        {
            "name": "separator",
            "description": "Separator character used in the CSV. Defaults to ','.",
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
        "Identifies the separator in a CSV file, supporting both commas and tabs. "
        "If detection fails, it provides the initial lines of the file for manual inspection."
    ),
    parameters=[
        {
            "name": "file_path",
            "description": "The relative path to the CSV file.",
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
        first_line = file.readline().strip()
        print(first_line)

        if "," in first_line:
            separator = ","
        elif "\t" in first_line:
            separator = "\\t"

    if separator:
        message = f"The separator used in the file is: {separator}"
        success = True
    else:
        with open(full_path, "r") as file:
            lines = [
                line.strip() for line in file.readlines()[:5]
            ]  # Read up to the first 5 lines if available
        sample_lines = "\n".join(lines)
        message = (
            f"Unable to detect the separator used in the file. "
            f"Please review the CSV file to ensure it is formatted correctly. "
            f"Here are the first few lines for your reference:\n{sample_lines}"
        )
        success = False

    return AbilityResult(
        ability_name="detect_csv_separator",
        ability_args={"file_path": file_path},
        success=success,
        message=message,
    )


# @ability(
#     name="csv_python_executor",
#     description=(
#         "Executes Python code on a CSV file using pandas DataFrame. The DataFrame is preloaded, "
#         "allowing direct manipulation. Provide the code snippet, and get the console output and any "
#         "created or modified files."
#     ),
#     parameters=[
#         {
#             "name": "separator",
#             "description": "Separator character used in the CSV. Defaults to ','.",
#             "type": "string",
#             "required": False,
#             "default": ",",
#         },
#         {
#             "name": "python_code",
#             "description": "Python code to manipulate the CSV data using pandas DataFrame.",
#             "type": "string",
#             "required": True,
#         },
#     ],
#     output_type="object",
# )
# async def csv_python_executor(
#     agent,
#     project: Project,
#     issue: Issue,
#     file_path: str,
#     separator: str = ",",
#     python_code: str = "",
# ) -> AbilityResult:
#     """
#     Run a python code
#     """
#     project_dir = agent.workspace.get_project_path_by_key(project.key)
#     # if "pd.read_csv" not in python_code:
#     #     python_code = (
#     #         f"df = pd.read_csv('{file_path}', sep='{separator}')\n{python_code}"
#     #     )
#     # else:
#     #     python_code = python_code.replace("CSV_FILE_PATH", f"{project_dir}/{file_path}")
#     python_code = sanitize_input(python_code)
#     python_repl = PythonAstREPLTool(
#         _globals=globals(), _locals=None, _working_directory=str(project_dir)
#     )

#     # TODO: find better approach
#     before_file_infos = agent.workspace.list_files_by_key(project.key)
#     output = python_repl.run(python_code)
#     after_file_infos = agent.workspace.list_files_by_key(project.key)

#     new_or_modified_files = []
#     for after_file_info in after_file_infos:
#         is_new = True
#         for before_file_info in before_file_infos:
#             if before_file_info["filename"] == after_file_info["filename"]:
#                 is_new = False
#                 if (
#                     before_file_info["updated_at"] != after_file_info["updated_at"]
#                     or before_file_info["filesize"] != after_file_info["filesize"]
#                 ):
#                     new_or_modified_files.append(
#                         {"file_info": after_file_info, "status": "modified"}
#                     )
#                 break
#         if is_new:
#             new_or_modified_files.append(
#                 {"file_info": after_file_info, "status": "new"}
#             )

#     activities = []
#     attachments = []
#     for file in new_or_modified_files:
#         file_info = file["file_info"]
#         new_attachment = Attachment(
#             url=file_info["relative_url"],
#             filename=file_info["filename"],
#             filesize=file_info["filesize"],
#         )

#         if file["status"] == "modified":
#             for old_attachment in issue.attachments:
#                 if old_attachment.filename == new_attachment.filename:
#                     issue.remove_attachment(old_attachment)
#                     break

#         activty = AttachmentUploadActivity(created_by=agent, attachment=new_attachment)
#         issue.add_attachment(new_attachment)
#         issue.add_activity(activty)

#         attachments.append(new_attachment)
#         activities.append(activty)

#     return AbilityResult(
#         ability_name="csv_python_executor",
#         ability_args={"python_code": python_code},
#         success=True,
#         message=str(output),
#         activities=activities,
#         attachments=attachments,
#     )
