import json
import os
import time

from typing import List, Optional, Dict, Any, Union
from langchain.document_loaders.chromium import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

from serpapi import GoogleSearch
from .selenium import browse_website


SERPAPI_MAX_ATTEMPTS = 3
GOOGLE_SEARCH_NUMBER = 5


async def extract_and_store_webpage_content(
    link, client, chunk_size: int = 1500, alias: Optional[str] = None, **kwargs
):
    """
    Extract and store the content of a webpage.

    Args:
        link (str): The URL of the webpage to be extracted.
        client (Any): The client instance to store the extracted content.
        chunk_size (int, optional): The size for each chunk of split content. Defaults to 1500.
        alias (Optional[str], optional): An alias for the webpage. Defaults to None.
    """
    text, links = await browse_website(link)
    doc = Document(page_content=text, metadata={"source": link})

    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=0)
    splitted_docs_list = splitter.split_documents([doc])

    with client.batch as batch:
        for doc in splitted_docs_list:
            data_object = {"link": link, "content": safe_google_results(doc.page_content), **kwargs}
            if alias:
                data_object["alias"] = alias
            batch.add_data_object(data_object, "Webpage")


def fetch_google_results(query, page: int, num: int = 5) -> List[Dict[Any, Any]]:
    """
    Fetch Google search results for a given query.

    Args:
        query (str): The search query.
        page (int): The page number of search results.
        num (int, optional): The number of search results to fetch. Defaults to 5.

    Returns:
        List[Dict[Any, Any]]: A list of dictionaries containing Google search results.
    """
    search_parameters = {
        "engine": "google",
        "q": query,
        "api_key": os.getenv("SERPAPI_API_KEY"),
        "start": page,
        "num": num,
    }
    attempts = 0
    while attempts < SERPAPI_MAX_ATTEMPTS:
        search = GoogleSearch(search_parameters)
        results = search.get_dict()
        search_results = list(results.get("organic_results", []))
        if search_results:
            return search_results

        time.sleep(1)
        attempts += 1
    return []


def safe_google_results(results: Union[str, List]) -> str:
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
