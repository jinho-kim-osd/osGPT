from typing import Optional, List, Any, Union, Dict
import json
import re
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


async def gpt4_chat_completion_request(
    messages: List[Dict[str, Any]],
    max_tokens: Optional[int] = None,
    stop: Optional[Union[str, List[str]]] = None,
    n: int = 1,
    functions: List[Dict[str, Any]] = [],
    **kwargs,
) -> Union[Dict[str, str], Dict[str, Dict]]:
    response = await chat_completion_request(
        messages=messages,
        model="gpt-4",
        temperature=0.4,
        top_p=0.3,
        # frequency_penalty=0.0,
        # presence_penalty=0.0,
        max_tokens=max_tokens,
        stop=stop,
        n=n,
        functions=functions,
        request_timeout=20,
        **kwargs,
    )
    if n > 1:
        res: List[str] = [""] * n
        for choice in response.choices:
            res[choice.index] = choice["message"]
        return res
    return response.choices[0]["message"]


def is_valid_json(json_str: str) -> bool:
    try:
        json.loads(json_str)
        return True
    except ValueError:
        return False


def extract_top_level_json(text: str) -> Optional[Dict]:
    text = text.replace(".encode()", "").replace(".encode('utf-8')", "")
    json_candidates = re.findall(r"(?<!\\)(?:\\\\)*\{(?:[^{}]|(?R))*\}", text)

    for candidate in json_candidates:
        if is_valid_json(candidate):
            return json.loads(candidate)
    return None


def top_level_json_field(text: str, field: str) -> Any:
    jsons = extract_top_level_json(text)

    if len(jsons) == 0:
        return ""
    for j in jsons:
        json_data = json.loads(j)
        if field in json_data:
            return json_data[field]
    return ""
