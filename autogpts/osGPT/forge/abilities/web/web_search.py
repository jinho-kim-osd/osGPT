from __future__ import annotations

import os
import json
import time
from itertools import islice
from bs4 import BeautifulSoup

from serpapi import GoogleSearch

from ..registry import ability
from ..schema import AbilityResult
from ...schema import Project, Issue
from ...utils import truncate_text
from ...agent import Agent
from ...message import AIMessage, UserMessage

SERPAPI_MAX_ATTEMPTS = 3


SYSTEM_PROMPT = """
Use the provided extracts (with sources)  to answer the question. 
Justify your answer by citing your sources, as in these examples:
When assigned a search task, conduct thorough internet searches to gather the necessary information.
Only report validated and verified information and ensure to include the source URL, title, a brief summary, and the priority level with the reasoning behind it.
Avoid including unverified or unvalidated information.
do not provide raw search results.
DO NOT SHOW THE FULL EXTRACT; only show the FIRST 3 words and LAST 3 words.  

Reply only in json with the following format:
{
    \"links\": [
        {
            \"url\": \"http://example.com/1\",
            \"title\": \"NVIDIA Annual Profit 2023\",
            \"summary\": \"The article provides an in-depth analysis of NVIDIA's annual profit for the year 2022.\",
            \"extracts\": \"Fourth-quarter revenue was $3.62 billion, up 11% from a year a ... down 6% from the previous quarter..\",
            \"priority\": 1,
            \"priority_reason\": \"Most recent data with detailed analysis\",
        },
        {
            \"url\": \"http://example.com/2\",
            \"title\": \"NVIDIA Financial Report 2020\",
            \"summary\": \"A comprehensive financial report of NVIDIA for the year 2020, including profits and expenses.\",
            \"extracts\": \"NVIDIA Revenue (Annual): 26.97B for Jan. 31, 2023. Revenue (Annual) Chart.\",
            \"priority\": 2,
            \"priority_reason\": \"Contains historical data, but not the most current\"
        }
        ... // Additional links can be added as needed
    ]
}
"""


@ability(
    name="web_search",
    description="Searches the web",
    parameters=[
        {
            "name": "query",
            "description": "The search query",
            "type": "string",
            "required": True,
        }
    ],
    output_type="object",
)
async def web_search(agent: Agent, project: Project, issue: Issue, query: str) -> AbilityResult:
    """Return the results of a Google search
    Args:
        query (str): The search query.
        num_results (int): The number of results to return.
    Returns:
        str: The results of the search.
    """
    search_results = []
    attempts = 0
    num_results = 8

    while attempts < SERPAPI_MAX_ATTEMPTS:
        if not query:
            return json.dumps(search_results)

        search = GoogleSearch(
            {
                "engine": "google",
                "q": query,
                "api_key": os.getenv("SERPAPI_API_KEY"),
            }
        )
        results = search.get_dict()
        search_results = list(islice(results["organic_results"], num_results))

        if search_results:
            break

        time.sleep(1)
        attempts += 1

    results = json.dumps(search_results, ensure_ascii=False, indent=4)
    safe_format_results = safe_google_results(results)
    message = await agent.think([AIMessage(content=SYSTEM_PROMPT), UserMessage(content=str(safe_format_results))])

    return AbilityResult(
        ability_name="web_search",
        ability_args={"query": query},
        success=True,
        message=message.content,
    )


def safe_google_results(results: str | list) -> str:
    """
        Return the results of a Google search in a safe format.
    Args:
        results (str | list): The search results.
    Returns:
        str: The results of the search.
    """
    if isinstance(results, list):
        safe_message = json.dumps([result.encode("utf-8", "ignore").decode("utf-8") for result in results])
    else:
        safe_message = results.encode("utf-8", "ignore").decode("utf-8")
    return safe_message
