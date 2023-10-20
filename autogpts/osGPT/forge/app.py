import os

from .jira_agent import JiraAgent
from .db import ForgeDatabase
from .on_boarding import setup_workspace

DATABASE_URI = os.getenv("DATABASE_STRING")
WORKSPACE_BASE_PATH = os.getenv("WORKSPACE_BASE_PATH")

db = ForgeDatabase(DATABASE_URI, debug_enabled=False)
workspace = setup_workspace(db)
print(workspace.display())

agent = JiraAgent(db, workspace)
app = agent.get_agent_app()
