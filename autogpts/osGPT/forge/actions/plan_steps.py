from typing import Dict, Any

from forge.sdk import Task, Action


class PlanStepsAction(Action):
    def __init__(self, task: Task):
        super().__init__("plan_steps")
        self.task = task
