from forge.sdk.forge_log import ForgeLogger
from .registry import ability
from .schema import AbilityResult
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
    output_type="object",
)
async def finish_work(
    agent,
    project: Project,
    issue: Issue,
    summary: str,
) -> AbilityResult:
    """
    A function to mark the end of a workday or work session and leave a summary note.

    Parameters:
        summary (str): A brief note on the work done or tasks accomplished during the session.

    Returns:
        A comment summarizing the day's activities.
    """
    comment = Comment(content=summary, created_by=agent)
    issue.add_activity(comment)
    return AbilityResult(
        ability_name="finish_work",
        ability_args={"summary": summary},
        success=True,
        message=None,
        activities=[comment],
    )
