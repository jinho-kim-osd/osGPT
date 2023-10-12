import json
import pprint
from typing import Optional, List

from forge.sdk import (
    Workspace,
    ForgeLogger,
)
from forge.db import ForgeDatabase
from .agent_base import ForgeAgentBase


logger = ForgeLogger(__name__)


class UserProxyAgent(ForgeAgentBase):
    def __init__(
        self,
        database: ForgeDatabase,
        workspace: Workspace,
        name: Optional[str] = "user-proxy",
        ability_names: Optional[List[str]] = ["run_python_code", "finish"],
    ):
        super().__init__(database, workspace, name, ability_names)
