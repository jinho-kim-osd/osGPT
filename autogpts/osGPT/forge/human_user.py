from typing import List, Optional

from .schema import User, UserType, Project, Issue, Activity, Comment


class HumanUser(User):
    type: UserType = UserType.HUMAN

    async def add_comment(
        self,
        project: Project,
        issue: Optional[Issue] = None,
    ) -> List[Activity]:
        # TODO: To be replace with Web UI interaction
        user_input = input("Add Comment: ")
        comment = Comment(content=user_input, created_by=self)
        issue.add_activity(comment)
        return [comment]
