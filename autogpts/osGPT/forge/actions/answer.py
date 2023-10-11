from typing import Dict, Any

from forge.sdk import Action, Task, Step


class AnswerAction(Action):
    def __init__(self, task: Task, step: Step, observation: Any):
        super().__init__("answer_chat")
        self.task = task
        self.step = step
        self.observation = observation
