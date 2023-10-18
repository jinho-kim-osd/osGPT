import os

from forge.sdk import LocalWorkspace
from .workspace import CollaborationWorkspace
from .jira_agent import JiraAgent
from .db import ForgeDatabase

DATABASE_URI = os.getenv("DATABASE_STRING")
WORKSPACE_BASE_PATH = os.getenv("WORKSPACE_BASE_PATH")

db = ForgeDatabase(DATABASE_URI, debug_enabled=False)
workspace = CollaborationWorkspace(
    name="Oscorp", service=LocalWorkspace(WORKSPACE_BASE_PATH)
)

agent = JiraAgent(db, workspace)
agent.setup_workspace()
app = agent.get_agent_app()
