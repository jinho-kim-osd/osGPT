import json

from forge.sdk import PromptEngine, ForgeLogger

from .utils import fetch_google_results, extract_and_store_webpage_content
from ..registry import ability
from ..schema import AbilityResult
from ...schema import Project, Issue
from ...agent import Agent
from ...message import AIMessage, UserMessage

SERPAPI_MAX_ATTEMPTS = 3
GOOGLE_SEARCH_NUMBER = 3
VECTOR_SEARCH_NUMBER_PER_PAGE = 1
CHUNK_SIZE = 2700


logger = ForgeLogger(__name__)


@ability(
    name="search_query",
    description="A web search for the specified query and returns the results.",
    parameters=[
        {
            "name": "query",
            "description": "The search query.",
            "type": "string",
            "required": True,
        },
        {
            "name": "page",
            "description": "The page number to display.",
            "type": "integer",
            "required": True,
            "default": 1,
        },
    ],
    output_type="object",
)
async def search_query(agent: Agent, project: Project, issue: Issue, query: str, page: int = 1) -> AbilityResult:
    search_results = fetch_google_results(query, page, GOOGLE_SEARCH_NUMBER)
    client = agent.workspace.vectorstore

    results = []
    for id, item in enumerate(search_results):
        logger.info("Scraping.." + item["link"] + item["title"] + item["snippet"])
        await extract_and_store_webpage_content(item["link"], client, CHUNK_SIZE, str(item["link"]))
        result = (
            client.query.get("Webpage", ["alias", "content"])
            .with_hybrid(query, alpha=0.7)
            .with_where({"path": ["alias"], "operator": "Equal", "valueText": str(item["link"])})
            .with_limit(VECTOR_SEARCH_NUMBER_PER_PAGE)
            .do()
        )
        results.append(result["data"]["Get"]["Webpage"])
    results = json.dumps(results, indent=4)
    logger.info("Vector Search Results:" + results)

    prompt_engine = PromptEngine("information-retrieval")
    system_message = prompt_engine.load_prompt("access-website-system")
    user_message = prompt_engine.load_prompt("access-website-user", query=issue.summary, page_content=results)

    response = await agent.think(messages=[AIMessage(content=system_message), UserMessage(content=user_message)])
    return AbilityResult(
        ability_name="search_query",
        ability_args={"query": query},
        success=True,
        message=response.content,
    )
