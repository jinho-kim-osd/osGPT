from forge.sdk import (
    ForgeLogger,
    PromptEngine,
)
from .agent import ForgeAgent

logger = ForgeLogger(__name__)


class UserProxyAgent(ForgeAgent):
    def _load_system_prompt(self, **kwargs) -> PromptEngine:
        return self.prompt_engine.load_prompt("user_proxy", name=self.name, **kwargs)
