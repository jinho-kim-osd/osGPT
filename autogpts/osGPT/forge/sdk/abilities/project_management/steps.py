from typing import Dict, Any, Optional
from ..registry import ability

from forge.sdk import Step


@ability(
    name="create_step",
    description="Create a new step",
    parameters=[
        {
            "name": "input",
            "description": "Input prompt for the step.",
            "type": "string",
            "required": True,
        },
        {
            "name": "is_last",
            "description": "Whether this is the last step in the task.",
            "type": "string",
            "required": True,
        },
        {
            "name": "additional_input",
            "description": "Additional input for the step",
            "type": "dict",
            "required": False,
        },
    ],
    output_type="dict",
)
async def create_step(
    agent,
    task_id: str,
    input: str,
    is_last: bool,
    additional_input: Optional[Dict[str, Any]] = None,
) -> Step:
    step = await agent.create_step(task_id, input, is_last, additional_input)
    return step.dict()


@ability(
    name="read_step",
    description="Read an existing step",
    parameters=[
        {
            "name": "step_id",
            "description": "Step ID",
            "type": "string",
            "required": True,
        },
    ],
    output_type="dict",
)
async def read_step(agent, task_id: str, step_id: str) -> Dict[str, Any]:
    step = await agent.db.get_step(task_id, step_id)
    return step.dict()


@ability(
    name="update_step",
    description="Update an existing step",
    parameters=[
        {
            "name": "step_id",
            "description": "Step ID",
            "type": "string",
            "required": True,
        },
        {
            "name": "status",
            "description": "The status of the task step.",
            "type": "Literal['created', 'running', 'completed']",
            "required": False,
        },
        {
            "name": "name",
            "description": "The name of the task step.",
            "type": "string",
            "required": False,
        },
        {
            "name": "output",
            "description": "Output of the task step.",
            "type": "string",
            "required": False,
        },
    ],
    output_type="bool",
)
async def update_step(
    agent,
    task_id: str,
    step_id: str,
    status: Optional[str] = None,
    name: Optional[str] = None,
    output: Optional[str] = None,
) -> bool:
    updated = await agent.db.update_step(task_id, step_id, status, name, output)
    return updated


# @ability(
#     name="delete_step",
#     description="Delete an existing step",
#     parameters=[
#         {
#             "name": "step_id",
#             "description": "Step ID",
#             "type": "string",
#             "required": True,
#         },
#     ],
#     output_type="bool",
# )
# async def delete_step(agent, task_id: str, step_id: str) -> bool:
#     deleted = await agent.db.delete_step(task_id, step_id)
#     return deleted
