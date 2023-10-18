from typing import Optional, List, Dict, Any
import json

from forge.sdk import ForgeLogger

from .agent_user import AgentUser
from .schema import (
    Project,
    Issue,
    IssueType,
    Comment,
    Activity,
    AssignmentChangeActivity,
)
from .contants import MAX_CHAT_REQUEST_RETRIES
from .utils import gpt4_chat_completion_request

logger = ForgeLogger(__name__)


MANAGE_WORKSPACE_PROMPT = """
"""


class ProjectManagerAgentUser(AgentUser):
    async def execute_project(
        self, task_id: str, project: Project, issue: Optional[Issue] = None
    ) -> List[Activity]:
        activities = []
        target_workspace_structure = await self.plan_project(project, issue)
        management_activities = await self.manage_workspace(
            task_id, target_workspace_structure, project, issue
        )
        activities.extend(management_activities)
        return activities

    async def clarify_requirements(
        self,
        requirements: str,
        project: Project,
        issue: Optional[Issue] = None,
    ) -> List[Activity]:
        activities = []
        logger.info(
            f"[{project.key}-{issue.id}] {self.name} > Clarifying requirements for the project"
        )
        system_prompt = self.build_system_prompt(template="clarify-requirements-system")
        user_prompt = self.build_system_prompt(
            template="clarify-requirements-user",
            requirements=requirements,
            current_workspace_structure=self.workspace.display_structure(),
        )
        openai_messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {"role": "user", "content": user_prompt},
        ]
        response = await gpt4_chat_completion_request(openai_messages)
        logger.info(f"[{project.key}-{issue.id}] {self.name} > {str(response)}")
        if "function_call" in response:
            fn_name = response["function_call"]["name"]
            fn_args = json.loads(response["function_call"]["arguments"])
            fn_activities = self.run_ability(fn_name, fn_args, project, issue)
            activities.extend(fn_activities)
        else:
            if response["content"] not in ["<CLARIFIED>"]:
                comment = Comment(content=response["content"], created_by=self)
                issue.add_attachment(comment)
                activities.append(comment)
        return activities

    async def plan_project(
        self,
        project: Project,
        issue: Optional[Issue] = None,
    ) -> Dict[str, Any]:
        logger.info(f"[{project.key}-{issue.id}] {self.name} > Planning a project")
        system_prompt = self.build_system_prompt(template="plan-project-system")
        user_prompt = self.build_system_prompt(
            template="plan-project-user",
            current_workspace_structure=self.workspace.display_structure(),
        )
        openai_messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {"role": "user", "content": user_prompt},
        ]
        response = await gpt4_chat_completion_request(openai_messages)
        logger.info(f"[{project.key}-{issue.id}] {self.name} > {str(response)}")
        return response

    async def manage_workspace(
        self,
        task_id: str,
        target_workspace_structure: str,
        project: Project,
        issue: Optional[Issue] = None,
        force_function: bool = True,
    ) -> List[Activity]:
        logger.info(f"[{project.key}-{issue.id}] {self.name} > Managing a workspace")
        activities = []

        logger.info(
            f"[{project.key}-{issue.id}] {self.name} > Requesting a function response"
        )
        system_prompt = self.build_system_prompt(template="manage-workspace-system")
        user_prompt = self.build_system_prompt(
            template="manage-workspace-user",
            current_workspace_structure=self.workspace.display_structure(),
            target_workspace_structure=target_workspace_structure,
        )
        openai_messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {"role": "user", "content": user_prompt},
        ]
        functions = self.abilities.list_abilities_for_function_calling()
        while True:
            response = await gpt4_chat_completion_request(
                openai_messages, functions=functions
            )
            logger.info(f"[{project.key}-{issue.id}] {self.name} > {str(response)}")
            if "function_call" in response:
                fn_name = response["function_call"]["name"]
                fn_args = json.loads(response["function_call"]["arguments"])
                fn_response = self.abilities.run_ability(
                    self.workspace, fn_name, **fn_args
                )
                if isinstance(fn_response, Activity):
                    activities.append(fn_response)
                else:
                    raise NotImplementedError
                break
            else:
                if force_function:
                    openai_messages.append(
                        {"role": "user", "content": "Use functions only."}
                    )
                else:
                    comment = Comment(content=response["content"], created_by=self)
                    issue.add_attachment(comment)
                    activities.append(comment)
                    break
        logger.info(str([str(activity) for activity in activities]))
        return activities

    def run_ability(
        self,
        fn_name: str,
        fn_args: Dict[str, Any],
        project: Project,
        issue: Optional[Issue] = None,
    ) -> List[Activity]:
        activities = []
        if fn_name == "view_comments":
            raise NotImplementedError

        elif fn_name == "add_comment":
            target_issue = self.workspace.get_issue(
                fn_args["project_key"], fn_args["issue_id"]
            )
            comment = Comment(content=fn_args["content"], created_by=self)
            target_issue.add_activity(comment)
            activities.append(comment)

        elif fn_name == "finish":
            ...
        return activities
