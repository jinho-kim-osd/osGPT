from typing import Optional, Dict

from pydantic import BaseModel


class Message(BaseModel):
    content: str
    sender_id: Optional[str]
    recipient_id: Optional[str]

    def to_openai_message(self, actor_id: Optional[str] = None) -> Dict[str, str]:
        if self.sender_id == self.recipient_id:
            role = "system"
            name = actor_id
        elif self.sender_id == actor_id:
            role = "assistant"
            name = self.recipient_id
        else:
            role = "user"
            name = self.sender_id
        return {"role": role, "content": self.content, "name": name}
