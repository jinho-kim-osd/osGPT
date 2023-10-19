# from typing import List
# from forge.sdk.forge_log import ForgeLogger
# from .registry import ability
# from .project_management.issues import change_issue_status, add_comment
# from ..schema import Project, Issue, Comment, Activity, Status

# logger = ForgeLogger(__name__)


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
