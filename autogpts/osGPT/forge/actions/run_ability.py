from typing import Dict, Any

from forge.sdk import Action, Task, Step


class RunAbilityAction(Action):
    def __init__(
        self,
        task: Task,
        step: Step,
        ability: Dict[str, Any] = {},
    ):
        super().__init__("run_ability")
        self.task = task
        self.step = step
        self.ability = ability
