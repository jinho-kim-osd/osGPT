import os

# from forge.agent import ForgeAgent
from forge.sdk import LocalWorkspace

from .master_agent import MasterAgent
from .db import ForgeDatabase

database_name = os.getenv("DATABASE_STRING")
workspace = LocalWorkspace(os.getenv("AGENT_WORKSPACE"))
database = ForgeDatabase(database_name, debug_enabled=False)
agent = MasterAgent(database=database, workspace=workspace)
app = agent.get_agent_app()
