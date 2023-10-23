import pandas as pd
import json

from ..registry import ability
from ..schema import AbilityResult
from ...schema import Project, Issue


MAX_STRING_LENGTH = 200


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
        {
            "name": "page",
            "description": "The page number to display.",
            "type": "integer",
            "required": False,
            "default": 1,
        },
    ],
    output_type="object",
)
async def read_csv(
    agent, project: Project, issue: Issue, file_path: str, separator: str = ",", page: int = 1
) -> AbilityResult:
    """
    Read data from a CSV file
    """
    project_root = agent.workspace.get_project_path_by_key(project.key)
    full_path = project_root / file_path

    df = pd.read_csv(full_path, sep=separator)

    # Estimate the number of rows that can be displayed within the MAX_STRING_LENGTH limit
    sample_data = df.head(1).to_string()
    avg_row_length = len(sample_data)
    estimated_rows_per_page = MAX_STRING_LENGTH // avg_row_length

    # Calculate the total number of pages
    total_rows = len(df)
    total_pages = -(-total_rows // estimated_rows_per_page)  # Calculate the ceiling of the division

    # Validate page number
    if page < 1 or page > total_pages:
        return AbilityResult(
            ability_name="read_csv",
            ability_args={"file_path": file_path, "separator": separator, "page": page},
            success=False,
            message=f"Invalid page number. Please select a page between 1 and {total_pages}.",
        )

    # Get the rows corresponding to the requested page
    start_row = (page - 1) * estimated_rows_per_page
    end_row = min(page * estimated_rows_per_page, total_rows)
    page_data = df.iloc[start_row:end_row].to_string()

    suffix = " ..." if total_pages != page else ""
    message = f"(Page {page}/{total_pages})\n{page_data}" + suffix

    return AbilityResult(
        ability_name="read_csv",
        ability_args={"file_path": file_path, "separator": separator, "page": page},
        success=True,
        message=message,
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
            lines = [line.strip() for line in file.readlines()[:5]]  # Read up to the first 5 lines if available
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
