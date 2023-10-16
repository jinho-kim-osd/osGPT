from typing import Optional, List, Any, Union, Dict
import json
import re

from forge.sdk import chat_completion_request, ForgeLogger

logger = ForgeLogger(__name__)


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
        temperature=0.2,  # Previous Value: 0.1
        top_p=0.2,
        frequency_penalty=0.0,
        presence_penalty=0.0,
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


def camel_to_snake(name: str) -> str:
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    name = re.sub(r"\s+", "_", name)
    return name.lower()


def is_valid_json(json_str: str) -> bool:
    try:
        json.loads(json_str)
        return True
    except ValueError:
        return False


def replace_prompt_placeholders(prompt: str, **variables: Any) -> str:
    placeholders = re.findall(r"\$\{(.+?)\}", prompt)
    if len(placeholders) == 0:
        return prompt

    for placeholder in placeholders:
        s = placeholder.split(".")
        variable_name = s[0]
        variable = variables[variable_name]
        if len(s) > 1:
            attr = s[-1]
            output = getattr(variable, attr, None)
        else:
            output = variable
        prompt = prompt.replace(f"${{{placeholder}}}", json.dumps(output))
    return prompt


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
