from typing import List
from forge.sdk.forge_log import ForgeLogger
from .registry import ability
from .project_management.issues import change_issue_status, add_comment
from ..schema import Project, Issue, Comment, Activity, Status

logger = ForgeLogger(__name__)


@ability(
    name="finish_work",
    description="Use this to mark the end of the workday or work session.",
    parameters=[
        {
            "name": "summary",
            "description": "A brief note on the work done or tasks accomplished during the session.",
            "type": "string",
            "required": True,
        }
    ],
    output_type="None",
)
async def finish_work(
    agent,
    project: Project,
    issue: Issue,
    summary: str,
) -> Comment:
    """
    A function to mark the end of a workday or work session and leave a summary note.

    Parameters:
        summary (str): A brief note on the work done or tasks accomplished during the session.

    Returns:
        A comment summarizing the day's activities.
    """
    comment = await add_comment(agent, project, issue, project.key, issue.id, summary)
    issue.add_activity(comment)
    return comment


# @ability(
#     name="finish",
#     description="Use this to close all issues once you have accomplished all of workspace issues.",
#     parameters=[
#         {
#             "name": "reason",
#             "description": "A summary to the user of how the goals were accomplished",
#             "type": "string",
#             "required": True,
#         }
#     ],
#     output_type="None",
# )
# async def finish(
#     agent,
#     project: Project,
#     issue: Issue,
#     reason: str,
# ) -> List[Activity]:
#     """
#     A function that takes in a string and exits the program

#     Parameters:
#         reason (str): A summary to the user of how the goals were accomplished.
#     Returns:
#         A result string from create chat completion. A list of suggestions to
#             improve the code.
#     """
#     activities = []
#     comment = await add_comment(agent, project, issue, project.key, issue.id, reason)
#     activities.append(comment)

#     for i in project.issues:
#         status_change_activity = await change_issue_status(
#             agent, project, issue, project.key, i.id, "Closed"
#         )
#         activities.append(status_change_activity)
#     return activities
