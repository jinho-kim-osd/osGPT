from typing import Dict, Any, List

from forge.sdk import Action, Task, Step


class CreatePlannedStepsAction(Action):
    def __init__(self, task: Task, step: Step, planned_steps: List[Step]):
        super().__init__("create_planned_steps")
        self.task = task
        self.step = step
        self.planned_steps = planned_steps
