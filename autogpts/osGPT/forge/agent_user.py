import os
import json
from typing import Optional, List, Any, Dict

from forge.sdk import (
    Agent,
    ForgeLogger,
    PromptEngine,
)
from .utils import get_openai_response
from .workspace import CollaborationWorkspace

from .abilities.registry import ForgeAbilityRegister
from .schema import User, Project, Issue, Comment, UserType, Activity
from .db import ForgeDatabase

logger = ForgeLogger(__name__)

# Maximum number of chained calls allowed to prevent infinite or lengthy loops
DEFAULT_MAX_CHAINED_CALLS = os.getenv("DEFAULT_MAX_CHAINED_CALLS")
TERMINATION_WORD = "<TERMINATE>"


class AgentUser(User, Agent):
    db: ForgeDatabase
    type: UserType = UserType.AGENT
    workspace: CollaborationWorkspace
    ability_names: Optional[List[str]]

    class Config:
        extra = "allow"

    def __str__(self):
        return f"AgentUser({self.name}, {self.role})"

    def __init__(self, **data):
        super().__init__(**data)
        self.abilities = ForgeAbilityRegister(self, self.ability_names)

    async def resolve_issues(
        self, project: Project, issue: Optional[Issue] = None
    ) -> List[Activity]:
        activities = []
        logger.info(
            f"[{project.key}-{issue.id if issue else 'No Issue'}] {self.name} > Resolving an issue"
        )

        # Execute the task, add your logic here
        task_execution_activities = await self.perform_task(project, issue)
        activities.extend(task_execution_activities)

        # Report the results
        # reporting_activities = await self.report_results(
        #     task_execution_activities, project, issue
        # )
        # activities.extend(reporting_activities)
        return activities

    async def process_chained_calls(
        self,
        project: Project,
        issue: Optional[Issue] = None,
        messages: List[Dict[str, Any]] = [],
        functions: Optional[Dict[str, Any]] = None,
        force_function: bool = False,
        max_chained_calls: int = DEFAULT_MAX_CHAINED_CALLS,
    ) -> List[Activity]:
        activities = []

        stack = 0
        prev_message_content = None
        while stack < max_chained_calls:
            logger.info(
                f"[{project.key}-{issue.id if issue else 'No Issue'}] > Process chained calls (stack: {stack})"
            )
            message = await get_openai_response(messages, functions=functions)

            if "function_call" in message:
                fn_name = message["function_call"]["name"]
                fn_args = json.loads(message["function_call"]["arguments"])
                logger.info(
                    f"[{project.key}-{issue.id if issue else 'No Issue'}] > Function request: {fn_name}({fn_args})"
                )
                try:
                    fn_response = await self.abilities.run_ability(
                        project, issue, fn_name, **fn_args
                    )
                    if isinstance(fn_response, Activity):
                        fn_response_str = str(fn_response)
                        activities.append(fn_response)
                    elif isinstance(fn_response, List):
                        fn_response_str = "["
                        for item in fn_response:
                            if isinstance(item, Activity):
                                fn_response_str += str(item) + ",\n"
                                activities.append(item)
                            else:
                                fn_response_str += str(item)
                        fn_response_str += "]"
                    else:
                        fn_response_str = str(fn_response)
                except Exception as e:
                    fn_response_str = str(e)
                messages.append(
                    {
                        "role": "function",
                        "name": fn_name,
                        "content": fn_response_str,
                    }
                )

                logger.info(
                    f"[{project.key}-{issue.id if issue else 'No Issue'}] > Function response: {fn_response_str}"
                )
            elif message["content"] in [TERMINATION_WORD, "", prev_message_content]:
                break
            else:
                if force_function:
                    logger.info(
                        f"[{project.key}-{issue.id if issue else 'No Issue'}] > Invalid Response."
                    )
                    messages.append({"role": "user", "content": "Use functions only."})
                else:
                    comment = Comment(content=message["content"], created_by=self)
                    logger.info(
                        f"[{project.key}-{issue.id if issue else 'No Issue'}] > {comment}"
                    )
                    issue.add_activity(comment)
                    messages.append({"role": "user", "content": project.display()})
                    activities.append(comment)
                    prev_message_content = message["content"]

            # Add workspace landscape for observation
            messages.append({"role": "user", "content": project.display()})
            stack += 1

        if stack >= max_chained_calls:
            logger.error(
                f"[{project.key}-{issue.id if issue else 'No Issue'}] > Reached max chained function calls: {max_chained_calls}"
            )

        return activities

    async def perform_task(
        self, project: Project, issue: Optional[Issue] = None
    ) -> List[Activity]:
        activities = []
        logger.info(
            f"[{project.key}-{issue.id if issue else 'No Issue'}] {self.name} > Performing a task"
        )

        workspace_role = self.workspace.get_workspace_role_with_user_name(self.name)
        system_prompt = self.build_system_prompt(
            template="perform-task-system", workspace_role=workspace_role
        )
        user_prompt = self.build_system_prompt(
            template="perform-task-user",
            current_workspace_structure=self.workspace.display(),
        )
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {"role": "user", "content": user_prompt},
        ]
        functions = self.abilities.list_abilities_for_function_calling()
        activities = await self.process_chained_calls(
            project,
            issue,
            messages,
            functions,
            force_function=True,
            max_chained_calls=2,
        )
        return activities

    def get_prompt_engine(self, model: str) -> PromptEngine:
        return PromptEngine(model)

    def build_system_prompt(
        self,
        model: Optional[str] = None,
        template: Optional[str] = None,
        **kwargs,
    ) -> str:
        if model is None:
            model = os.getenv("DEFAULT_PROMPT_MODEL", "predefined")
        prompt_engine = self.get_prompt_engine(model=model)
        if template is None:
            template = self.id
        return prompt_engine.load_prompt(template, **kwargs)
