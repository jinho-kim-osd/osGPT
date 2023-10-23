from typing import List, Optional

from ..schema import User, UserType, Project, Issue, Activity, Comment


class HumanUser(User):
    type: UserType = UserType.HUMAN

    async def add_comment(
        self,
        project: Project,
        issue: Optional[Issue] = None,
    ) -> List[Activity]:
        """
        TODO: This method is currently under development and not in use.
        It is intended to be replaced with a Web UI interaction in the future.
        """

        # Note: The below implementation is a placeholder and will be refined
        # as the development progresses.
        user_input = input("Add Comment: ")
        comment = Comment(content=user_input, created_by=self)
        issue.add_activity(comment)
        return [comment]
