from typing import Optional, List, Dict
from pydantic import BaseModel

from forge.sdk.db import Artifact


class AgentThoughts(BaseModel):
    task: Optional[str]
    question: Optional[str]
    thought: str
    initial_answer: Optional[str]
    final_answer: Optional[str]
    observation: Optional[str]


class AgentAction(BaseModel):
    action: str
    action_args: Dict
    log: str


class AgentObservation(BaseModel):
    content: Optional[str]
    artifacts: List[Artifact]
    log: str

    class Config:
        arbitrary_types_allowed = True
