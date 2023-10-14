from typing import Optional, Dict, Any

from pydantic import BaseModel


class Message(BaseModel):
    content: str
    sender_id: Optional[str]
    recipient_id: Optional[str]
    function_call: Optional[Dict[str, Any]]

    def to_openai_message(self, actor_id: Optional[str] = None) -> Dict[str, str]:
        if self.sender_id == self.recipient_id:
            role = "system" if self.function_call is None else "function"
            name = actor_id
        elif self.sender_id == actor_id:
            role = "assistant"
            name = self.recipient_id
        else:
            role = "user"
            name = self.sender_id
        # return {"role": role, "content": self.content, "name": name}
        openai_message = {"role": role, "content": self.content}
        if role == "function":
            openai_message["name"] = actor_id
        return openai_message
