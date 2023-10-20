from typing import Optional, Dict, Any

from forge.sdk import ForgeLogger, PromptEngine

from .agent_user import AgentUser
from .schema import (
    Project,
    Issue,
    User,
)
from .utils import get_openai_response

logger = ForgeLogger(__name__)


class ProjectManagerAgentUser(AgentUser):
    async def select_worker(
        self,
        project: Project,
    ) -> Optional[User]:
        prompt_engine = PromptEngine("select-worker")
        workspace_role = self.workspace.get_workspace_role_with_user_name(self.name)
        system_prompt = prompt_engine.load_prompt(
            template="system", workspace_role=workspace_role
        )
        user_prompt = prompt_engine.load_prompt(
            template="user",
            current_project=project.display(),
        )
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {"role": "user", "content": user_prompt},
        ]
        message = await get_openai_response(messages)
        logger.info(
            f"[{project.key}] {self.name} > Next speaker is {message['content']}"
        )
        if message["content"] == "<TERMINATE>":
            return None
        speaker = self.workspace.get_user_with_name(message["content"])
        return speaker

    async def review_issue(
        self,
        project: Project,
        issue: Issue,
    ) -> Dict[str, Any]:
        return await self.execute_task_with_prompt(
            project,
            issue,
            "review-issue",
            [
                "create_issue",
                "change_assinee",
                "change_issue_status",
                "read_file",
                "add_comment",
            ],
        )

    async def decide_reopen(
        self,
        project: Project,
        issue: Issue,
    ) -> Dict[str, Any]:
        return await self.execute_task_with_prompt(
            project,
            issue,
            "decide-reopen",
            [
                "create_issue",
                "change_assinee",
                "change_issue_status",
                "read_file",
                "list_files",
                "add_comment",
            ],
        )
