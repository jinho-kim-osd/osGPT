from typing import Dict, Any

from forge.sdk import Action, Task, Step


class ExecuteStepAction(Action):
    def __init__(self, task: Task, step: Step):
        super().__init__("execute_step")
        self.task = task
        self.step = step
