import glob
import importlib
import inspect
import os
from typing import Any, List

from forge.sdk.abilities.registry import Ability, AbilityRegister, AbilityParameter
from ..schema import Project, Issue


def ability(
    name: str, description: str, parameters: List[AbilityParameter], output_type: str
):
    def decorator(func):
        func_params = inspect.signature(func).parameters
        param_names = set(
            [AbilityParameter.parse_obj(param).name for param in parameters]
        )
        param_names.add("agent")
        param_names.add("project")
        param_names.add("issue")
        func_param_names = set(func_params.keys())
        if param_names != func_param_names:
            raise ValueError(
                f"Mismatch in parameter names. Ability Annotation includes {param_names}, but function acatually takes {func_param_names} in function {func.__name__} signature"
            )
        func.ability = Ability(
            name=name,
            description=description,
            parameters=parameters,
            method=func,
            output_type=output_type,
        )
        return func

    return decorator


class ForgeAbilityRegister(AbilityRegister):
    def register_abilities(self) -> None:
        if len(self.ability_names) > 0:
            for ability_path in glob.glob(
                os.path.join(os.path.dirname(__file__), "**/*.py"), recursive=True
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
                            f".{ability[:-3]}", package="forge.abilities"
                        )
                        for attr in dir(module):
                            func = getattr(module, attr)

                            if hasattr(func, "ability"):
                                ab = func.ability
                                if not ab.name in self.ability_names:
                                    continue

                                ab.category = (
                                    ability.split(".")[0].lower().replace("_", " ")
                                    if len(ability.split(".")) > 1
                                    else "general"
                                )
                                self.abilities[func.ability.name] = func.ability
                    except Exception as e:
                        print(f"Error occurred while registering abilities: {str(e)}")

    async def run_ability(
        self, project: Project, issue: Issue, ability_name: str, *args: Any, **kwds: Any
    ) -> Any:
        try:
            ability = self.abilities[ability_name]
            return await ability(self.agent, project, issue, *args, **kwds)
        except Exception:
            raise
