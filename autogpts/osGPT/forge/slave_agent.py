from typing import List

from forge.sdk import (
    Workspace,
    ForgeLogger,
)
from forge.db import ForgeDatabase
from .agent_base import ForgeAgentBase


logger = ForgeLogger(__name__)


class SlaveAgent(ForgeAgentBase):
    def __init__(
        self,
        database: ForgeDatabase,
        workspace: Workspace,
        name: str = "slave",
        ability_names: List[str] | None = None,
        system_message: str | None = None,
    ):
        super().__init__(database, workspace, name, ability_names, system_message)
