from .schema import User, UserType


class HumanUser(User):
    type: UserType = UserType.HUMAN
