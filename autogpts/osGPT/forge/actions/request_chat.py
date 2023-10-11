from typing import Dict, Any

from forge.sdk import Action, Task, Step


class RequestChatAction(Action):
    def __init__(self, task: Task, step: Step):
        super().__init__("request_chat")
        self.task = task
        self.step = step
