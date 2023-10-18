import json
from typing import Optional, List, Any, Dict

from forge.sdk import (
    Agent,
    Step,
    StepRequestBody,
    ForgeLogger,
    Task,
    TaskRequestBody,
    Artifact,
    PromptEngine,
)
from .utils import gpt4_chat_completion_request
from .workspace import CollaborationWorkspace

from .contants import (
    DEFAULT_AGENT_USER_PROMPT_MODEL,
)
from .abilities.registry import ForgeAbilityRegister
from .schema import User, Project, Issue, Comment, Attachment, UserType, Activity
from .db import ForgeDatabase

logger = ForgeLogger(__name__)


class AgentUser(User, Agent):
    db: ForgeDatabase
    type: UserType = UserType.AGENT
    workspace: CollaborationWorkspace
    ability_names: Optional[List[str]]

    class Config:
        extra = "allow"

    def __init__(self, **data):
        super().__init__(**data)
        self.abilities = ForgeAbilityRegister(self, self.ability_names)

    async def execute_project(
        self, task_id: str, project: Project, issue: Issue
    ) -> List[Activity]:
        activities = []
        logger.info(f"[{project.key}-{issue.id}] {self.name} > Executing a project")

        # Execute the task, add your logic here
        task_execution_activities = await self.perform_task(project, issue)

        # Report the results
        reporting_activities = await self.report_results(
            task_id, task_execution_activities, project, issue
        )
        activities.extend(reporting_activities)
        return activities

    async def perform_task(self, project: Project, issue: Issue) -> List[Activity]:
        activities = []
        logger.info(f"[{project.key}-{issue.id}] {self.name} > Performing a task")

        workspace_role = self.workspace.get_workspace_role_with_user_name(self.name)
        system_prompt = self.build_system_prompt(
            template="perform-task-system", workspace_role=workspace_role
        )
        user_prompt = self.build_system_prompt(
            template="perform-task-user",
            current_workspace_structure=self.workspace.display_structure(),
        )
        openai_messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {"role": "user", "content": user_prompt},
        ]
        functions = self.abilities.list_abilities_for_function_calling()
        response = await gpt4_chat_completion_request(
            openai_messages, functions=functions
        )
        logger.info(f"[{project.key}-{issue.id}] {self.name} > {str(response)}")
        if "function_call" in response:
            fn_name = response["function_call"]["name"]
            fn_args = json.loads(response["function_call"]["arguments"])
            fn_activities = self.run_ability(fn_name, fn_args, project, issue)
            activities.extend(fn_activities)
        else:
            comment = Comment(content=response["content"], created_by=self)
            issue.add_attachment(comment)
            activities.append(comment)
        return activities

    async def report_results(
        self,
        task_id: str,
        task_execution_activities: List[Activity],
        project: Project,
        issue: Issue,
    ) -> List[Activity]:
        activities = []

        workspace_role = self.workspace.get_workspace_role_with_user_name(self.name)
        system_prompt = self.build_system_prompt(
            template="report-results-system",
            workspace_role=workspace_role,
        )
        user_prompt = self.build_system_prompt(
            template="report-results-user",
            task_execution_activities=task_execution_activities,
            current_workspace_structure=self.workspace.display_structure(),
        )
        openai_messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {"role": "user", "content": user_prompt},
        ]
        functions = self.abilities.list_abilities_for_function_calling()
        response = await gpt4_chat_completion_request(
            openai_messages, functions=functions
        )
        logger.info(f"[{project.key}-{issue.id}] {self.name} > {str(response)}")
        if "function_call" in response:
            fn_name = response["function_call"]["name"]
            fn_args = json.loads(response["function_call"]["arguments"])
            fn_activities = self.run_ability(fn_name, fn_args, project, issue)
            activities.extend(fn_activities)
        else:
            comment = Comment(content=response["content"], created_by=self)
            issue.add_attachment(comment)
            activities.append(comment)
        logger.info(f"[{project.key}-{issue.id}] {self.name} > {str(response)}")

        comment_content = f"Task completed with results: {response}"
        comment = Comment(content=comment_content, created_by=self, attachments=[])
        issue.add_activity(comment)
        activities.append(comment)
        return activities

    async def manage_workspace(
        self,
        task_id: str,
        target_workspace_structure: str,
        project: Project,
        issue: Optional[Issue] = None,
    ) -> List[Activity]:
        activities = []
        while True:
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
            response = await gpt4_chat_completion_request(
                openai_messages, functions=functions
            )
            logger.info(str(response))
            if "function_call" in response:
                fn_name = response["function_call"]["name"]
                fn_args = json.loads(response["function_call"]["arguments"])
                logger.info(f"Function Calling[{self.name}]: {fn_name}({fn_args})")
                fn_activities = self.run_ability(fn_name, fn_args, project, issue)
                activities.extend(fn_activities)
                break
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
        if fn_name == "change_assignee":
            target_issue = self.workspace.get_issue(
                fn_args["project_key"], fn_args["issue_id"]
            )
            old_assignee = target_issue.assignee
            new_assignee = self.workspace.get_user_with_name(fn_args["new_assignee"])
            target_issue.assignee = new_assignee
            activity = AssignmentChangeActivity(
                old_assignee=old_assignee, new_assignee=new_assignee, created_by=self
            )
            target_issue.add_activity(activity)
            activities.append(activity)

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

    def get_prompt_engine(
        self, model: str = DEFAULT_AGENT_USER_PROMPT_MODEL
    ) -> PromptEngine:
        return PromptEngine(model)

    def build_system_prompt(
        self,
        model: str = DEFAULT_AGENT_USER_PROMPT_MODEL,
        template: Optional[str] = None,
        **kwargs,
    ) -> str:
        prompt_engine = self.get_prompt_engine(model=model)
        if template is None:
            template = self.id
        return prompt_engine.load_prompt(template, **kwargs)

    async def create_step(
        self,
        task_id: str,
        input: str,
        name: Optional[str] = None,
        additional_input: Optional[dict] = None,
    ) -> Step:
        if name is None:
            name = input
        step_request = StepRequestBody(
            name=name, input=input, additional_input=additional_input
        )
        return await self.db.create_step(
            task_id=task_id, input=step_request, additional_input=additional_input
        )

    def reset(self):
        pass

    async def create_task(self, task_request: TaskRequestBody) -> Task:
        self.reset()
        return await super().create_task(task_request)
