from forge.sdk.forge_log import ForgeLogger
from ..registry import ability
from ..schema import AbilityResult
from ...schema import Project, Issue
from ...agent_user import AgentUser

logger = ForgeLogger(__name__)

@ability(
    name="review_code",
    description=(
        "Review the specified Python file against the provided requirements. Returns review results."
    ),
    parameters=[
        {
            "name": "file_path",
            "description": "Path of the Python file to review.",
            "type": "string",
            "required": True,
        },
        {
            "name": "requirements",
            "description": "Requirements or criteria for the code review.",
            "type": "string",
            "required": True,
        },
    ],
    output_type="object",
)
async def review_code(
    agent: AgentUser,
    project: Project,
    issue: Issue,
    file_path: str,
    requirements: str
) -> AbilityResult:
    """
    Review the specified Python file based on the given requirements.
    """
    code = agent.workspace.read_by_key(key=project.key, path=file_path)
    thought = await agent.think("code-review", {"job_title": agent.job_title}, {"requirements": requirements, "code": code})
    return AbilityResult(
        ability_name="review_code",
        ability_args={"file_path": file_path, "requirements": requirements},
        success=True,
        message=thought
    )
