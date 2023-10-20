from forge.sdk.forge_log import ForgeLogger
from .registry import ability
from .project_management.issues import add_comment
from ..schema import Project, Issue, Comment

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
    return comment
