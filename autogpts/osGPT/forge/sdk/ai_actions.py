from abc import ABC


class Action(ABC):
    def __init__(self, name: str):
        self.name = name
