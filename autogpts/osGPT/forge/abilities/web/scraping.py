import json
from typing import Optional

from forge.sdk import PromptEngine
from .utils import extract_and_store_webpage_content
from ...agent import Agent
from ..registry import ability
from ...schema import Project, Issue
from ..schema import AbilityResult
from ...message import AIMessage, UserMessage

VECTOR_SEARCH_LIMIT = 5


@ability(
    name="access_website",
    description="Extracts and prioritizes the useful information from the search results.",
    parameters=[
        {"name": "link", "description": "The URL of the websites to access", "type": "string", "required": True},
        {
            "name": "query",
            "description": "The search query to specify which information to retrieve.",
            "type": "string",
            "required": False,
        },
    ],
    output_type="object",
)
async def access_website(agent: Agent, project: Project, issue: Issue, link: str, query: Optional[str] = None):
    """
    Access the specified website, store its content in vectorstore, and perform a vector search.
    """
    # Use the issue summary as the default query if none is provided.
    query = query or issue.summary

    client = agent.workspace.vectorstore

    # Extract the content from the provided link and store it in vectorstore with a specified alias.
    await extract_and_store_webpage_content(link, client, 1500, alias=query)

    # Perform a vector search on the stored webpage content to find and prioritize relevant information.
    search_result = (
        client.query.get("Webpage", ["link", "content"]).with_hybrid(query).with_limit(VECTOR_SEARCH_LIMIT).do()
    )

    prompt_engine = PromptEngine("information-retrieval")
    system_message = prompt_engine.load_prompt("extract-website-system")
    user_message = prompt_engine.load_prompt(
        "extract-website-user", query=issue.summary, page_content=json.dumps(search_result, indent=4)
    )

    # Let the agent process and think about the messages to generate a response.
    response = await agent.think(messages=[AIMessage(content=system_message), UserMessage(content=user_message)])

    return AbilityResult(
        ability_name="access_website",
        ability_args={"link": link, "query": query},
        success=True,
        message=response.content,
    )
