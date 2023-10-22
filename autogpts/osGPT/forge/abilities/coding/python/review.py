import json

from forge.sdk.forge_log import ForgeLogger
from ...registry import ability
from ...schema import AbilityResult
from ....schema import Project, Issue, Comment, Attachment, AttachmentUploadActivity
from ....agent_user import AgentUser

logger = ForgeLogger(__name__)

@ability(
    name="review_code",
    description=(
        "Review and potentially refine the specified Python file according to the project’s current status and conditions."
    ),
    parameters=[
        {
            "name": "file_path",
            "description": "Path of the Python file to review.",
            "type": "string",
            "required": True,
        }
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
    Reviews and, if necessary, refines the specified Python file based on the current status and conditions of the project.
    Provides a comment on the actions taken or recommended next steps.
    """
    old_code = agent.workspace.read_by_key(key=project.key, path=file_path)
    
    thought = await agent.think("code-review", {"job_title": agent.job_title}, {"project": project.display(), "code": old_code})
    parsed_output = json.loads(thought)
    
    refined_code = parsed_output.get("refined_code")
    comment = parsed_output.get("comment")

    # If refined code is provided, update the file; otherwise, skip the update.
    if refined_code:
        file_info = agent.workspace.write_file_by_key(key=project.key, path=file_path, data=refined_code.encode())

        # Log the updated file as an attachment.
        new_attachment = Attachment(
            url=file_info["relative_url"],
            filename=file_info["filename"],
            filesize=file_info["filesize"],
        )

        issue.remove_attachment(file_name)
        issue.add_attachment(new_attachment)
        upload_activity = AttachmentUploadActivity(created_by=agent, attachment=new_attachment)
        issue.add_activity(upload_activity)
    else:
        new_attachment = None

    if refined_code and isinstance(refined_code, str):
        refined_code = refined_code.encode()

    # Add a comment regarding the review and potential refinements made.
    comment = Comment(
        created_by=agent,
        content=comment,
        attachments=[new_attachment] if new_attachment else [],
    )
    issue.add_activity(comment)
    

    return AbilityResult(
        ability_name="review_code",
        ability_args={"file_path": file_path},
        success=True,
        message=thought if refined_code else "No code update was necessary.",
        activities=[comment],
        attachments=[new_attachment] if new_attachment else [],
    )