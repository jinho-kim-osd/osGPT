from __future__ import annotations

import os
import json
import time
from itertools import islice

from serpapi import GoogleSearch


SERPAPI_MAX_ATTEMPTS = 3


def web_search(agent, task_id: str, query: str) -> str:
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
                "api_key": "7928d2ae227ff648bbf3380fd8d2c55b1bdbc286fea3936d131bd81b8e48b5fe",
            }
        )
        results = search.get_dict()
        print(results)
        search_results = list(islice(results["organic_results"], num_results))

        if search_results:
            break

        time.sleep(1)
        attempts += 1

    results = json.dumps(search_results, ensure_ascii=False, indent=4)
    return safe_google_results(results)


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


if __name__ == "__main__":
    web_search("hi", "hi", "How is Tesla addressing challenges?")
