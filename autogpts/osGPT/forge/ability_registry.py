import glob
import importlib
import os
from typing import List, Optional

from forge.sdk.abilities.registry import AbilityRegister


class ForgeAbilityRegister(AbilityRegister):
    def __init__(self, agent, ability_names: Optional[List[str]] = None) -> None:
        self._ability_names = ability_names
        self.abilities = {}
        self.agent = agent
        self.register_abilities(ability_names)

    def register_abilities(self, ability_names: Optional[List[str]] = None) -> None:
        if ability_names:
            for ability_path in glob.glob(
                os.path.join(os.path.dirname(__file__), "sdk", "abilities", "**/*.py"),
                recursive=True,
            ):
                if not os.path.basename(ability_path) in [
                    "__init__.py",
                    "registry.py",
                ]:
                    ability = os.path.relpath(
                        ability_path, os.path.dirname(__file__)
                    ).replace("/", ".")
                    try:
                        module = importlib.import_module(
                            f".{ability[:-3]}", package="forge"
                        )
                        for attr in dir(module):
                            func = getattr(module, attr)
                            if hasattr(func, "ability"):
                                ab = func.ability

                                ab.category = (
                                    ability.split(".")[0].lower().replace("_", " ")
                                    if len(ability.split(".")) > 1
                                    else "general"
                                )
                                if func.ability.name in ability_names:
                                    self.abilities[func.ability.name] = func.ability
                    except Exception as e:
                        print(f"Error occurred while registering abilities: {str(e)}")
