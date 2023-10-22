import unittest
from io import StringIO
import sys
from ...registry import ability
from ...schema import AbilityResult
from ....schema import Project, Issue, Comment
from forge.sdk import ForgeLogger

logger = ForgeLogger(__name__)

@ability(
    name="execute_unit_tests",
    description="Execute unit tests from the provided Python test and source files in the workspace.",
    parameters=[
        {
            "name": "source_file_name",
            "description": "Name of the Python source file to be tested.",
            "type": "string",
            "required": True,
        },
        {
            "name": "test_file_content",
            "description": "Content of the Python test file to be executed.",
            "type": "string",
            "required": True,
        }
    ],
    output_type="object",
)
async def execute_unit_tests(
    agent, project: Project, issue: Issue, source_file_name: str, test_file_content: str
) -> AbilityResult:
    """
    Execute unit tests from a provided Python test file against the specified source file
    """
    project_root = agent.workspace.get_project_path_by_key(project.key)

    # Automatically generate the test file name based on the source file name
    test_file_name = f"test_{source_file_name}"
    test_file_path = project_root / test_file_name

    # Write the test file to the workspace
    with open(test_file_path, 'w') as test_file:
        test_file.write(test_file_content)

    # Ensure the source file exists
    source_file_path = project_root / source_file_name
    if not source_file_path.exists():
        raise FileNotFoundError(f"The source file '{source_file_name}' does not exist.")

    # Redirect stdout to capture the test results
    capturedOutput = StringIO()
    sys.stdout = capturedOutput

    # Execute the tests
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(test_file_path.parent), pattern=test_file_name)
    runner = unittest.TextTestRunner(stream=sys.stdout)
    result = runner.run(suite)

    # Reset stdout to normal
    sys.stdout = sys.__stdout__

    test_results = capturedOutput.getvalue()

    comment = Comment(
        created_by=agent,
        content=f"Executed unit tests from {test_file_name} against {source_file_name}. Here are the results:\n\n```\n{test_results}\n```"
    )
    issue.add_activity(comment)

    return AbilityResult(
        ability_name="execute_unit_tests",
        ability_args={
            "source_file_name": source_file_name,
            "test_file_content": test_file_content,
        },
        success=result.wasSuccessful(),
        message="Unit tests executed successfully." if result.wasSuccessful() else "Some unit tests failed.",
        activities=[comment],
    )
