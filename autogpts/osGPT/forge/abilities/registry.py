import glob
import importlib
import inspect
import os
from typing import Any, List

from forge.sdk.abilities.registry import Ability, AbilityRegister, AbilityParameter
from ..schema import Workspace


def ability(
    name: str, description: str, parameters: List[AbilityParameter], output_type: str
):
    def decorator(func):
        func_params = inspect.signature(func).parameters
        param_names = set(
            [AbilityParameter.parse_obj(param).name for param in parameters]
        )
        param_names.add("agent")
        param_names.add("workspace")
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
        self, workspace: Workspace, ability_name: str, *args: Any, **kwds: Any
    ) -> Any:
        """
        This method runs a specified ability with the provided arguments and keyword arguments.

        The agent is passed as the first argument to the ability. This allows the ability to access and manipulate
        the agent's state as needed.

        Args:
            workspace (Workspace): The ID of the task that the ability is being run for.
            ability_name (str): The name of the ability to run.
            *args: Variable length argument list.
            **kwds: Arbitrary keyword arguments.

        Returns:
            Any: The result of the ability execution.

        Raises:
            Exception: If there is an error in running the ability.
        """
        try:
            ability = self.abilities[ability_name]
            return await ability(self.agent, workspace, *args, **kwds)
        except Exception:
            raise
