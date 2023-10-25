import json
from typing import List, Optional, Dict, Any, Union
from langchain.document_loaders.chromium import Document
from langchain.document_loaders import AsyncChromiumLoader
from langchain.document_transformers import BeautifulSoupTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter

import os
import json
import time

from serpapi import GoogleSearch


SERPAPI_MAX_ATTEMPTS = 3
GOOGLE_SEARCH_NUMBER = 5


TAGS_TO_EXTRACT = [
    "p",
    "li",
    "div",
    "a",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "span",
    "strong",
    "em",
    "blockquote",
    "pre",
    "code",
    "td",
    "th",
    "tspan",
]


async def extract_and_store_webpage_content(
    link, client, chunk_size: int = 1500, alias: Optional[str] = None
) -> List[str]:
    """
    Extract and store the content of a webpage.

    Args:
        link (str): The URL of the webpage to be extracted.
        client (Any): The client instance to store the extracted content.
        chunk_size (int, optional): The size for each chunk of split content. Defaults to 1500.
        alias (Optional[str], optional): An alias for the webpage. Defaults to None.

    Returns:
        List[str]: A list of UUIDs of the stored webpage contents.
    """
    loader = AsyncChromiumLoader([])
    html_content = await loader.ascrape_playwright(link)
    doc = Document(page_content=html_content, metadata={"source": link})

    bs_transformer = BeautifulSoupTransformer()
    docs_transformed = bs_transformer.transform_documents([doc], tags_to_extract=TAGS_TO_EXTRACT)

    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=0)
    splitted_docs_list = splitter.split_documents(docs_transformed)

    uuids = []
    for doc in splitted_docs_list:
        data_object = {
            "link": link,
            "content": safe_google_results(doc.page_content),
        }
        if alias:
            data_object["alias"] = alias
        try:
            uuid = client.data_object.create(data_object=data_object, class_name="Webpage")
            uuids.append(uuid)
        except Exception as e:
            print(e)
    return uuids


def fetch_google_results(query, page, num: int = 5) -> List[Dict[Any, Any]]:
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
