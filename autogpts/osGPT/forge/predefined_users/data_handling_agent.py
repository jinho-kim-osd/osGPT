from typing import List

from forge.sdk import ForgeLogger

from ..agent import Agent

logger = ForgeLogger(__name__)


class DataHandlingAgent(Agent):
    ability_names: List[str] = [
        "change_issue_status",
        "add_comment",
        "read_file",
        "write_file",
        "list_files",
        "detect_csv_separator",
        "read_csv",
        "execute_python_code",
        "finish_work",
    ]
