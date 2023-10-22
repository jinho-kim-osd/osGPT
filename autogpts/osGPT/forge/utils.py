from typing import Optional, List, Any, Union, Dict
from datetime import datetime

from forge.sdk import chat_completion_request, ForgeLogger

logger = ForgeLogger(__name__)


def humanize_time(timestamp: datetime) -> str:
    delta = datetime.now() - timestamp

    if delta.total_seconds() < 60:
        return "just now"

    if delta.total_seconds() < 3600:
        minutes = delta.total_seconds() // 60
        return f"{int(minutes)} minute(s) ago"

    if delta.total_seconds() < 86400:
        hours = delta.total_seconds() // 3600
        return f"{int(hours)} hour(s) ago"

    days = delta.total_seconds() // 86400
    return f"{int(days)} day(s) ago"


def truncate_text(text: str, max_length=50) -> str:
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text


# TEMPORAL SOLUTION
import openai
import os
from tenacity import retry, stop_after_attempt, wait_random_exponential

openai.api_key = os.getenv("OPENAI_API_KEY")


@retry(wait=wait_random_exponential(min=1, max=40), stop=stop_after_attempt(3))
async def get_openai_response(
    messages: List[Dict[str, Any]],
    functions: Optional[Dict[str, Any]] = None,
    function_call: Optional[str] = None,
    temperature: float = 0.3,
    top_p: float = 0.2,
    presence_penalty: float = 0,
    frequency_penalty: float = 0,
    n: int = 1,
    request_timeout: int = 20,
    **kwargs,
) -> Union[Dict[str, str], Dict[str, Dict]]:
    if functions and function_call is None:
        function_call = "auto"
    completion_kwrags = {
        "model": "gpt-4",
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "presence_penalty": presence_penalty,
        "frequency_penalty": frequency_penalty,
        "request_timeout": request_timeout,
        **kwargs,
    }
    if functions is not None:
        completion_kwrags.update({"functions": functions})
    if function_call is not None:
        completion_kwrags.update({"function_call": function_call})

    response = await chat_completion_request(
        **completion_kwrags,
        **kwargs,
    )
    if n > 1:
        res: List[str] = [""] * n
        for choice in response.choices:
            res[choice.index] = choice["message"]
        return res
    return response.choices[0]["message"]
