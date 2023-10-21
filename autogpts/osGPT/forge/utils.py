from typing import Optional, List, Any, Union, Dict
import json
import re
from datetime import datetime
import requests

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
    # top_p: float = 0.75,
    presence_penalty: float = 0,
    frequency_penalty: float = 0,
    n: int = 1,
    **kwargs,
) -> Union[Dict[str, str], Dict[str, Dict]]:
    if functions and function_call is None:
        function_call = "auto"
    # We use HTTP requests for timeout
    # headers = {
    #     "Content-Type": "application/json",
    #     "Authorization": "Bearer " + openai.api_key,
    # }
    json_data = {
        "model": "gpt-4",
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "presence_penalty": presence_penalty,
        "frequency_penalty": frequency_penalty,
        **kwargs,
    }
    if functions is not None:
        json_data.update({"functions": functions})
    if function_call is not None:
        json_data.update({"function_call": function_call})
    # try:
    #     response = requests.post(
    #         "https://api.openai.com/v1/chat/completions",
    #         headers=headers,
    #         json=json_data,
    #         timeout=30,
    #     )
    #     response = response.json()
    # except Exception as e:
    #     print("Unable to generate ChatCompletion response")
    #     print(f"Exception: {e}")
    #     return e
    # if n > 1:
    #     res: List[str] = [""] * n
    #     for choice in response["choices"]:
    #         res[choice["index"]] = choice["message"]
    #     return res
    # return response["choices"][0]["message"]

    # response = openai.ChatCompletion.create(
    #     model="gpt-4",
    #     messages=messages,
    #     temperature=temperature,
    #     top_p=top_p,
    #     max_tokens=max_tokens,
    #     functions=functions,
    #     function_call="auto",
    #     n=n,
    #     stop=stop,
    #     **kwargs
    #     # presence_penalty=0.0,
    #     # frequency_penalty=0.0,
    # )
    ## NOTE: Litellm is not reliable for me
    response = await chat_completion_request(
        **json_data
        # messages=messages,
        # model="gpt-4",
        # temperature=temperature,
        # top_p=top_p,
        # frequency_penalty=frequency_penalty,
        # presence_penalty=presence_penalty,
        # n=n,
        # functions=functions,
        # request_timeout=20,
        # **kwargs,
    )
    if n > 1:
        res: List[str] = [""] * n
        for choice in response.choices:
            res[choice.index] = choice["message"]
        return res
    return response.choices[0]["message"]


def parse_json(json_str: str):
    # We are using a very rudimentary way to clean up the escape characters.
    # This should be adjusted according to the actual needs and scenarios.
    cleaned_json_str = (
        json_str.replace("\\\\", "\\")
        .replace('\\"', '"')
        .replace("\\n", "\n")
        .replace("\\t", "\t")
    )

    try:
        # Try to parse the JSON string directly
        return json.loads(json_str)
    except json.JSONDecodeError:
        escaped_json_str = json_str.encode("unicode_escape").decode()
        return json.loads(cleaned_json_str)
