from typing import Optional, Dict, Any
import json
from enum import Enum
from pydantic import BaseModel


class FunctionCall(BaseModel):
    """
    A model to represent the details of a function call, including the function's name and its arguments.
    """

    name: str
    arguments: Optional[Dict[str, Any]] = None


class Role(str, Enum):
    """
    Enum to represent the role of a message sender within a conversation.
    """

    USER = "user"
    SYSTEM = "system"
    ASSISTANT = "assistant"
    FUNCTION = "function"


class Message(BaseModel):
    """
    A model to represent messages in a conversation, capable of being transformed into a format compatible with the OpenAI API.
    """

    role: Role
    content: Optional[str]
    function_call: Optional[FunctionCall] = None
    sender: Optional[str] = None
    recipient: Optional[str] = None

    def to_openai_message(self) -> Dict[str, Any]:
        """
        Convert the message to a dictionary format compatible with the OpenAI API, filtering out any None values.

        Returns:
            A dictionary representing the message, ready for the OpenAI API.
        """
        message = {k: v for k, v in self.dict().items() if v is not None}

        if message.get("name") == "":
            del message["name"]

        if message["role"] == "function" and "function_call" in message and "arguments" in message["function_call"]:
            message["function_call"]["arguments"] = json.dumps(message["function_call"]["arguments"])
        if message["role"] == "function":
            message["name"] = message["function_call"]["name"]
            del message["function_call"]
        return message


class SystemMessage(Message):
    """
    A specialized message class for system-level messages.
    """

    role: Role = Role.SYSTEM


class UserMessage(Message):
    """
    A specialized message class for user messages.
    """

    role: Role = Role.USER


class AIMessage(Message):
    """
    A specialized message class for assistant messages.
    """

    role: Role = Role.ASSISTANT


class FunctionMessage(Message):
    """
    A specialized message class for representing function calls within a conversation.
    """

    role: Role = Role.FUNCTION
