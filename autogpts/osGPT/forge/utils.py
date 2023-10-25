import os
import ast
import uuid
import re
from contextlib import contextmanager
import hashlib
from pathlib import Path
from typing import Optional, Sequence, Any, Dict, List, Tuple
from datetime import datetime

from .message import Message, Role, FunctionCall
from forge.sdk import chat_completion_request, ForgeLogger

logger = ForgeLogger(__name__)


@contextmanager
def change_cwd(path: str):
    """
    A context manager to temporarily change the current working directory.

    Args:
        path (str): The path to change the current working directory to.
    """
    prev_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


def string_to_uuid_md5(s: str) -> uuid.UUID:
    """
    Generate a UUID based on the MD5 hash of a given string.

    Args:
        s: The input string.

    Returns:
        uuid.UUID: The UUID generated from the MD5 hash of the input string.
    """
    return uuid.uuid5(uuid.NAMESPACE_DNS, s)


def calculate_checksum(file_path: Path) -> str:
    """
    Calculate the SHA-256 checksum of a file.

    Args:
        file_path: Path to the file.

    Returns:
        str: The SHA-256 checksum of the file.
    """
    with open(file_path, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    return file_hash


def humanize_time(timestamp: datetime) -> str:
    """
    Converts a datetime timestamp into a human-readable string.

    Args:
        timestamp (datetime): The datetime to convert.

    Returns:
        str: A human-readable string representation of the time difference from now.
    """
    delta = datetime.now() - timestamp

    # Define time intervals and their respective messages
    intervals = [
        (60, "just now"),
        (3600, "{:.0f} minute(s) ago"),
        (86400, "{:.0f} hour(s) ago"),
    ]

    # Find and return the appropriate message based on the time delta
    seconds = delta.total_seconds()
    for interval, message in intervals:
        if seconds < interval:
            return message.format(seconds / (interval / 60))

    return f"{delta.total_seconds() // 86400:.0f} day(s) ago"


def truncate_text(text: str, max_length=50) -> str:
    """
    Truncates a string to the specified maximum length and adds an ellipsis if truncated.

    Args:
        text (str): The text to truncate.
        max_length (int, optional): The maximum length of the truncated string. Defaults to 50.

    Returns:
        str: The truncated string with an ellipsis added if it was truncated.
    """
    return text[:max_length] + "..." if len(text) > max_length else text


async def invoke(
    messages: Sequence[Message],
    functions: Optional[Dict[str, Any]] = None,
    function_call: Optional[str] = None,
    model: str = "gpt-4",
    temperature: float = 0.3,
    top_p: float = 0.2,
    presence_penalty: float = 0,
    frequency_penalty: float = 0,
    request_timeout: int = 120,
    max_tokens: int = 2000,
    **kwargs,
) -> Message:
    """
    Invoke a model completion with the provided messages and parameters.

    Args:
        ... (various): Various arguments for configuring the model invocation and message.

    Returns:
        Message: The model's generated message.
    """
    # Convert messages to the format suitable for OpenAI API
    openai_messages = [msg.to_openai_message() for msg in messages]

    # Prepare the completion request
    completion_args = {
        "model": model,
        "messages": openai_messages,
        "temperature": temperature,
        "top_p": top_p,
        "presence_penalty": presence_penalty,
        "frequency_penalty": frequency_penalty,
        "request_timeout": request_timeout,
        "max_tokens": max_tokens,
        "n": 1,
        **kwargs,
    }

    # If there are functions available, add them to the request
    if functions:
        completion_args["functions"] = functions
        function_call = function_call or "auto"

    # If a function call is specified, add it to the request
    if function_call:
        completion_args["function_call"] = function_call

    # Request a completion from the OpenAI API
    response = await chat_completion_request(**completion_args)
    openai_message = response.choices[0]["message"]

    # Process the response to create a FunctionCall object if a function was called
    if "function_call" in openai_message:
        fn_name = openai_message["function_call"]["name"]
        fn_args = ast.literal_eval(openai_message["function_call"]["arguments"].strip())
        function_call = FunctionCall(name=fn_name, arguments=fn_args)
    else:
        function_call = None

    # Return the assistant's message
    return Message(
        role=Role(openai_message["role"]),
        content=openai_message["content"],
        function_call=function_call,
    )


def parse_code_blocks(chat: str) -> List[Tuple[str, str, str]]:
    """Extracts code blocks with file paths from a chat.

    This function extracts code blocks of the format:
    ```language
    # path/to/file
    code content
    ```

    Args:
        chat (str): The chat to extract code blocks from.

    Returns:
        List[Tuple[str, str, str]]: A list of tuples. Each tuple contains:
            - The programming language (as a string).
            - The file path (as a string).
            - The corresponding code block content (as a string).

    Example:
        chat_example = '''
        Hello!
        ```python
        # some/path/example.py
        print("Hello, World!")
        ```
        '''
        parse_code_blocks(chat_example)
        # Returns: [('python', 'some/path/example.py', 'print("Hello, World!")\n')]
    """
    regex = r"```(\S+)\s*#?\s*([\S\s]+?)\n(.*?)```"
    matches = re.findall(regex, chat, re.DOTALL)
    return matches
