import json
import requests
from collections import defaultdict
from pathlib import Path
from uuid import uuid4
from shutil import copy2

AGENT_API_ENDPOINT = "http://127.0.0.1:8000/ap/v1"

# Task Setup
WORKSPACE_BASE_PATH = Path("agbenchmark_config/workspace")

CHALLENGES_DIR = Path("../../benchmark/agbenchmark/challenges")

# # Abilities
# CHALLENGE = "abilities/read_file"  # Clear
# CHALLENGE = "abilities/write_file"  # Clear
# # Alignment
# CHALLENGE = "alignment/1_distraction" # TODO: Database?
# CHALLENGE = "alignment/2_injection"
# # Code
# CHALLENGE = "verticals/code/1_three_sum"
# CHALLENGE = "verticals/code/2_password_generator"
# CHALLENGE = "verticals/code/3_file_organizer"
# CHALLENGE = "verticals/code/4_url_shortener"
# CHALLENGE = "verticals/code/5_tic_tac_toe"
# CHALLENGE = "verticals/code/6_battleship"
# # Data
# CHALLENGE = "verticals/data/1_sort_csv"  # Clear
CHALLENGE = "verticals/data/2_label_csv"  # Clear
# CHALLENGE = "verticals/data/3_combine_csv"  # Clear
# CHALLENGE = "verticals/data/4_answer_question_small_csv"  # Clear
# CHALLENGE = "verticals/data/5_answer_question_csv"  # Clear
# CHALLENGE = "verticals/data/6_answer_question_combine_csv"  # Clear
# # Scrape
# CHALLENGE = "verticals/scrape/1_search"
# CHALLENGE = "verticals/scrape/2_book_price"
# CHALLENGE = "verticals/scrape/3_revenue_retrieval"
# CHALLENGE = "verticals/scrape/4_revenue_retrieval_2"
# CHALLENGE = "verticals/scrape/5_get_information"
# # Synthesize
# CHALLENGE = "verticals/synthesize/1_basic_content_gen"

CHALLENGE_PATH = (CHALLENGES_DIR / CHALLENGE).resolve()

CHALLENGES = {}
task_informations = defaultdict(dict)

# Read and print task from data.json
data_json_path = CHALLENGE_PATH / "data.json"
if data_json_path.exists() and data_json_path.is_file():
    with open(data_json_path, "r") as file:
        data = json.load(file)

        if "eval_id" not in data:
            data["eval_id"] = str(uuid4())

        task_input = data.get("task")
        print(task_input)
else:
    print(f"{data_json_path} does not exist or is not a file.")


# Create a new task
task_create_response = requests.post(
    f"{AGENT_API_ENDPOINT}/agent/tasks",
    json={"input": task_input},
)
if task_create_response.status_code == 200:
    task_id = task_create_response.json().get("task_id")
    print(f"Task {task_id} created.")

    # Copy files from artifacts_in to PROJECT_BASE_PATH, only if artifacts_in exists
    artifacts_in_path = CHALLENGE_PATH / "artifacts_in"
    if artifacts_in_path.exists() and artifacts_in_path.is_dir():
        project_path = (WORKSPACE_BASE_PATH / task_id).resolve()
        project_path.mkdir(parents=True, exist_ok=True)
        for item in artifacts_in_path.iterdir():
            if item.is_file():
                print(item)
                copy2(item, project_path)
    else:
        print(f"{artifacts_in_path} does not exist, skipping copy.")

    is_first_step = True
    while True:  # Keep looping until we break out of it
        step_input = task_input if is_first_step else None
        step_response = requests.post(
            f"{AGENT_API_ENDPOINT}/agent/tasks/{task_id}/steps",
            json={"input": step_input},
        )

        if step_response.status_code == 200:
            step_data = step_response.json()
            print(step_data["output"])

            # Stop further requests if it's the last step
            if step_data.get("is_last"):
                print("This is the last step, stopping further requests.")
                break  # Exit the loop
            is_first_step = False
        else:
            print("Failed to execute step")
            break  # Optional: Exit the loop on failure, remove if you want to keep trying
else:
    print("Failed to create task.")
