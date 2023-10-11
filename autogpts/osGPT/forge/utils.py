from typing import Optional, Tuple, List, Any, Union, Literal, Dict
import json
import regex

from forge.sdk import chat_completion_request, ForgeLogger

logger = ForgeLogger(__name__)


async def gpt4_chat_completion_request(
    messages: List[Dict[str, Any]],
    max_tokens: Optional[int] = None,
    stop: Optional[Union[str, List[str]]] = None,
    n: int = 1,
) -> Union[str, List[str]]:
    response = await chat_completion_request(
        messages=messages,
        model="gpt-4",
        temperature=0.0,
        top_p=1,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        max_tokens=max_tokens,
        stop=stop,
        n=n,
    )
    if n > 1:
        res: List[str] = [""] * n
        for choice in response.choices:
            res[choice.index] = choice["message"]["content"]
        return res
    return response.choices[0]["message"]["content"]


def is_valid_json(json_str: str) -> bool:
    try:
        json.loads(json_str)
        return True
    except ValueError:
        return False


def replace_prompt_placeholders(prompt: str, **variables: Any) -> str:
    placeholders = regex.findall(r"\$\{(.+?)\}", prompt)
    if len(placeholders) == 0:
        return prompt

    logger.info("Original Prompt!!: " + str(prompt))
    for placeholder in placeholders:
        logger.info("PlaceHolder: " + placeholder)
        s = placeholder.split(".")
        variable_name = s[0]
        logger.info("variable_name: " + variable_name)
        variable = variables[variable_name]
        logger.info("variables: " + str(variables))
        logger.info("variable: " + str(variable))
        if len(s) > 1:
            attr = s[-1]
            output = getattr(variable, attr, None)
        else:
            output = variable
        prompt = prompt.replace(f"${{{placeholder}}}", json.dumps(output))
    return prompt


def extract_top_level_json(text: str) -> Optional[Dict]:
    text = text.replace(".encode()", "").replace(".encode('utf-8')", "")
    json_candidates = regex.findall(r"(?<!\\)(?:\\\\)*\{(?:[^{}]|(?R))*\}", text)

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
