import os
import weaviate

WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
WEAVIATE_URL = os.getenv("WEAVIATE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def initialize_vectorstore() -> weaviate.Client:
    client = weaviate.Client(
        url=WEAVIATE_URL,
        auth_client_secret=weaviate.AuthApiKey(api_key=WEAVIATE_API_KEY),
        additional_headers={
            "X-OpenAI-Api-Key": OPENAI_API_KEY,
        },
    )
    # to start from scratch by deleting ALL data
    client.schema.delete_all()

    # ===== Create Article class for the schema =====
    webpage_class = {
        "class": "Webpage",
        "vectorizer": "text2vec-openai",
        "moduleConfig": {
            "generative-openai": {},
            "text2vec-openai": {"model": "ada", "modelVersion": "002", "type": "text", "vectorizeClassName": False},
        },
        "properties": [
            {
                "name": "link",
                "description": "The url of the webpage",
                "dataType": ["text"],
                "moduleConfig": {"text2vec-openai": {"skip": True}},
            },
            {
                "name": "snippet",
                "description": "The snippet of the webpage",
                "dataType": ["text"],
                "moduleConfig": {"text2vec-openai": {"skip": True}},
            },
            {
                "name": "alias",
                "description": "The alias",
                "dataType": ["text"],
                "moduleConfig": {"text2vec-openai": {"skip": True}},
            },
            {
                "name": "content",
                "description": "The content of the article",
                "dataType": ["text"],
            },
        ],
    }
    client.schema.create_class(webpage_class)
    return client
