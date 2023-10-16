from typing import Optional, Dict, Any

from datetime import datetime
from pydantic import BaseModel, Field


class Message(BaseModel):
    content: str
    sender_id: Optional[str]
    recipient_id: Optional[str]
    function_call: Optional[Dict[str, Any]]
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_openai_message(self, actor_id: Optional[str] = None) -> Dict[str, str]:
        if self.function_call:
            role = "function"
        elif self.sender_id == self.recipient_id:
            role = "system"
        elif actor_id == self.sender_id:
            role = "assistant"
        # actor_id,
        elif actor_id in self.recipient_id:
            role = "user"
        elif actor_id not in [self.sender_id, self.recipient_id]:  # Other Agent
            role = "user"
        else:
            raise ValueError(f"Error: {actor_id} {self.sender_id} {self.recipient_id}")
        openai_message = {
            "role": role,
            "content": self.content,
        }
        if role == "function":
            openai_message["name"] = self.function_call["name"]
        return openai_message
