from __future__ import annotations

import os
import json
import time
from itertools import islice

from serpapi import GoogleSearch

from ..registry import ability
from ..schema import AbilityResult
from ...schema import Project, Issue

SERPAPI_MAX_ATTEMPTS = 3


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
async def web_search(
    agent, project: Project, issue: Issue, query: str
) -> AbilityResult:
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
    return AbilityResult(
        ability_name="web_search",
        ability_args={"query": query},
        success=True,
        message=str(safe_format_results),
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
        safe_message = json.dumps(
            [result.encode("utf-8", "ignore").decode("utf-8") for result in results]
        )
    else:
        safe_message = results.encode("utf-8", "ignore").decode("utf-8")
    return safe_message
