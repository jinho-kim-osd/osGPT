from __future__ import annotations

from abc import abstractmethod
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field
from .utils import humanize_time, truncate_text
from .display import TreeStructureDisplay


class IconBaseModel(BaseModel):
    icon: str


class UserType(str, Enum):
    """
    Enumeration of user types.
    """

    HUMAN = "Human"
    AGENT = "Agent"


class Role(str, Enum):
    """
    User roles within a workspace.
    """

    OWNER = "Owner"
    ADMIN = "Admin"
    MEMBER = "Member"
    GUEST = "Guest"


class User(BaseModel):
    """
    A model representing a user, containing their ID, name, and assigned role.
    """

    id: str
    name: str
    role: Role

    class Config:
        arbitrary_types_allowed = True

    @abstractmethod
    async def resolve_issue(
        self, project: Project, issue: Optional[Issue] = None
    ) -> List[Activity]:
        raise NotImplementedError


class IssueType(str, Enum):
    """
    Enumeration of potential issue types.
    """

    EPIC = "Epic"
    TASK = "Task"
    STORY = "Story"
    BUG = "Bug"
    SUBTASK = "Subtask"


class Status(str, Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    REOPENED = "Reopened"
    CLOSED = "Closed"


class ActivityType(str, Enum):
    COMMENT = "Comment"
    ATTACHMENT_UPLOAD = "Attachment Upload"
    ASSIGNMENT_CHANGE = "Assignment Change"
    STATUS_CHANGE = "Status Change"
    ISSUE_CREATION = "Issue Creation"
    ISSUE_DELETION = "Issue Deletion"


class Activity(BaseModel):
    type: ActivityType
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: User

    class Config:
        arbitrary_types_allowed = True


class Attachment(IconBaseModel):
    """
    Represents a file attachment associated with a comment.
    """

    icon: str = "📎"
    url: str
    filename: str
    filesize: int
    uploaded_at: datetime = Field(default_factory=datetime.now)

    def __str__(self):
        humanized_time = humanize_time(self.uploaded_at)
        return (
            f"{self.icon} File: {self.filename}, Size: {self.filesize} bytes, "
            f"Uploaded on: {humanized_time}"
        )

    def __hash__(self):
        return hash((self.filename, self.filesize, self.url))


class Comment(Activity):
    type: ActivityType = ActivityType.COMMENT
    content: str
    attachments: List[Attachment] = Field(default_factory=list)

    def __str__(self):
        humanized_time = humanize_time(self.created_at)
        # truncated_comment = truncate_text(self.content, 200)
        return f"{self.created_by.name} added a Comment: '{self.content}'. {humanized_time}"

    def add_attachment(self, attachment: Attachment):
        """
        Add an attachment to the comment.
        """
        self.attachments.append(attachment)


class AttachmentUploadActivity(Activity):
    type: ActivityType = ActivityType.ATTACHMENT_UPLOAD
    attachment: Attachment

    def __str__(self):
        humanized_time = humanize_time(self.created_at)
        return (
            f"{self.created_by.name} added an Attachment: '{self.attachment.filename}'. "
            f"{humanized_time}"
        )


class AssignmentChangeActivity(Activity):
    type: ActivityType = ActivityType.ASSIGNMENT_CHANGE
    old_assignee: Optional[User]
    new_assignee: User

    def __str__(self) -> str:
        humanized_time = humanize_time(self.created_at)
        return (
            f"{self.created_by.name} changed the Assignee from "
            f"{self.old_assignee.name if self.old_assignee else 'None'} to "
            f"{self.new_assignee.name}. {humanized_time}"
        )


class StatusChangeActivity(Activity):
    type: ActivityType = ActivityType.STATUS_CHANGE
    old_status: Status
    new_status: Status

    def __str__(self):
        humanized_time = humanize_time(self.created_at)
        return (
            f"{self.created_by.name} changed the Status {self.old_status} → "
            f"{self.new_status}. {humanized_time}"
        )


class IssueCreationActivity(Activity):
    type: ActivityType = ActivityType.ISSUE_CREATION

    def __str__(self):
        humanized_time = humanize_time(self.created_at)
        return f"{self.created_by.name} created the Issue. {humanized_time}"


class IssueDeletionActivity(Activity):
    type: ActivityType = ActivityType.ISSUE_DELETION

    def __str__(self):
        humanized_time = humanize_time(self.created_at)
        return f"{self.created_by.name} delete the Issue. {humanized_time}"


class Issue(IconBaseModel):
    icon: str = "📋"
    id: int
    summary: str
    description: Optional[str]
    type: IssueType
    status: Status = Status.OPEN
    assignee: Optional[User]
    reporter: User
    parent_issue: Optional[Issue] = Field(None, alias="parentIssue")
    child_issues: List[Issue] = Field(default_factory=list, alias="childIssues")
    activities: List[Activity] = Field(default_factory=list)
    attachments: List[Attachment] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True

    def __str__(self):
        assignee_str = (
            f", Assignee: {self.assignee.name}" if self.assignee else ", Assignee: None"
        )
        return f"{self.icon} Issue #{self.id}: {self.summary} (Status: {self.status}{assignee_str})"

    def add_activity(self, activity: Activity):
        self.activities.append(activity)

    def add_attachment(self, attachment: Attachment):  # And added this method
        self.attachments.append(attachment)

    def display(self) -> str:
        tree_display = TreeStructureDisplay()

        issue_node = tree_display.add_node(str(self))

        # Add Parent Issue if exists
        if self.parent_issue:
            tree_display.add_node(
                f"Parent: {str(self.parent_issue)}", parent=issue_node
            )

        # Add Sub Issues if exist
        if self.child_issues:
            for child_issue in self.child_issues:
                tree_display.add_node(f"Sub: {str(child_issue)}", parent=issue_node)

        # Sorting activities by their creation time
        sorted_activities = sorted(self.activities, key=lambda x: x.created_at)

        for activity in sorted_activities:
            activity_node = tree_display.add_node(str(activity), parent=issue_node)

            if isinstance(activity, Comment) and activity.attachments:
                # Sorting attachments by their upload time within each activity
                print(activity.attachments)
                sorted_attachments = sorted(
                    activity.attachments, key=lambda x: x.uploaded_at
                )
                for attachment in sorted_attachments:
                    tree_display.add_node(str(attachment), parent=activity_node)

        # Sorting attachments by their upload time at the issue level
        sorted_issue_attachments = sorted(self.attachments, key=lambda x: x.uploaded_at)
        for attachment in sorted_issue_attachments:
            tree_display.add_node(str(attachment), parent=issue_node)

        return tree_display.display()


class Condition(BaseModel):
    description: str


class Transition(BaseModel):
    name: str
    source_status: Status
    destination_status: Status
    conditions: List[Condition] = Field(default_factory=list)

    def is_valid(self, issue: Issue) -> bool:
        # Here, you can add checks based on the conditions for the transition.
        # For simplicity, we'll just ensure the issue's current status matches the transition's source status.
        return issue.status == self.source_status


class Workflow(BaseModel):
    name: str
    transitions: List[Transition]

    def get_valid_transitions(self, issue: Issue) -> List[Transition]:
        return [t for t in self.transitions if t.is_valid(issue)]

    def execute_transition(self, issue: Issue, transition_name: str) -> bool:
        transition = next(
            (
                t
                for t in self.transitions
                if t.name == transition_name and t.is_valid(issue)
            ),
            None,
        )
        if transition:
            issue.status = transition.destination_status
            return True
        return False


class Project(IconBaseModel):
    icon: str = "📁"
    name: str
    key: str
    project_leader: User
    default_assignee: Optional[User]
    issues: List[Issue] = Field(default_factory=list)
    workflow: Workflow

    class Config:
        arbitrary_types_allowed = True

    def __str__(self):
        return f"{self.icon} Project {self.name} (Key: {self.key}, Leader: {self.project_leader.name})"

    def add_issue(self, issue: Issue):
        self.issues.append(issue)

    def apply_transition(
        self, issue: Issue, transition_name: str
    ):  # Added this method to apply transitions to issues
        if self.workflow.execute_transition(issue, transition_name):
            print(
                f"Transition '{transition_name}' applied to issue #{issue.id}. New status: {issue.status}"
            )
        else:
            print(
                f"Failed to apply transition '{transition_name}' to issue #{issue.id}"
            )

    def display(self) -> str:
        tree_display = TreeStructureDisplay()

        project_node = tree_display.add_node(str(self))

        # Sorting issues by the time of their most recent activity
        sorted_issues = sorted(
            self.issues,
            key=lambda x: max(
                [a.created_at for a in x.activities], default=datetime.min
            ),
        )

        for issue in sorted_issues:
            issue_node = tree_display.add_node(str(issue), parent=project_node)

            # Sorting activities by their creation time within each issue
            sorted_activities = sorted(issue.activities, key=lambda x: x.created_at)
            for activity in sorted_activities:
                activity_node = tree_display.add_node(str(activity), parent=issue_node)

                if isinstance(activity, Comment) and activity.attachments:
                    # Sorting attachments by their upload time within each activity
                    sorted_attachments = sorted(
                        activity.attachments, key=lambda x: x.uploaded_at
                    )
                    for attachment in sorted_attachments:
                        tree_display.add_node(str(attachment), parent=activity_node)

            # Sorting attachments by their upload time at the issue level
            sorted_issue_attachments = sorted(
                issue.attachments, key=lambda x: x.uploaded_at
            )
            for attachment in sorted_issue_attachments:
                tree_display.add_node(str(attachment), parent=issue_node)

        return tree_display.display()


class WorkspaceMember(IconBaseModel):
    icon = "👤"
    user: User
    workspace_role: str
    additional_info: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"

    def __str__(self):
        return f"{self.icon} {self.user.name} (Role: {self.workspace_role})"

    def add_info(self, key: str, value: Any):
        self.additional_info[key] = value


class Workspace(IconBaseModel):
    icon: str = "🌐"
    name: str
    projects: List[Project] = Field(default_factory=list)
    members: List[WorkspaceMember] = Field(default_factory=list)

    def __str__(self):
        return f"{self.icon} Workspace: {self.name}"

    def reset(self):
        self.projects = []
        self.members = []

    def get_issue(self, project_key: str, issue_id: int) -> Issue:
        """
        Get a specific issue in a project using the project key and issue ID.
        """
        project = self.get_project_with_key(project_key)
        if not project:
            raise ValueError(f"No project found with key {project_key}")

        issue = next((issue for issue in project.issues if issue.id == issue_id), None)
        if not issue:
            raise ValueError(
                f"No issue found with ID {issue_id} in project {project_key}"
            )

        return issue

    def add_project(self, project: Project):
        self.projects.append(project)

    def get_project(self, project_name: str) -> Project:
        for project in self.projects:
            if project.name == project_name:
                return project
        raise ValueError

    def get_project_with_key(self, project_key: str) -> Project:
        for project in self.projects:
            if project.key == project_key:
                return project
        raise ValueError

    def add_member(self, user: User, workspace_role: str, **kwargs):
        member = WorkspaceMember(
            user=user, workspace_role=workspace_role, additional_info=kwargs
        )
        self.members.append(member)

    def get_user_with_name(self, name: str) -> User:
        for member in self.members:
            if member.user.name == name:
                return member.user
        raise ValueError

    def get_users_with_role(self, role: Role) -> List[User]:
        return [member.user for member in self.members if member.user.role == role]

    def get_users_with_workspace_role(self, workspace_role: str) -> List[User]:
        return [
            member.user
            for member in self.members
            if member.workspace_role == workspace_role
        ]

    def get_workspace_role_with_user_name(self, name: str) -> str:
        for member in self.members:
            if name == member.user.name:
                return member.workspace_role
        raise ValueError

    def display(self) -> str:
        tree_display = TreeStructureDisplay()

        workspace_node = tree_display.add_node(str(self))

        for member in self.members:
            tree_display.add_node(str(member), parent=workspace_node)

        for project in self.projects:
            project_node = tree_display.add_node(str(project), parent=workspace_node)

            # Sorting issues by their ID in ascending order
            sorted_issues = sorted(project.issues, key=lambda x: x.id)

            # # Sorting issues by the time of their most recent activity
            # sorted_issues = sorted(
            #     project.issues,
            #     key=lambda x: max(
            #         [a.created_at for a in x.activities], default=datetime.min
            #     ),
            # )

            for issue in sorted_issues:
                issue_node = tree_display.add_node(str(issue), parent=project_node)

                # Sorting activities by their creation time within each issue
                sorted_activities = sorted(issue.activities, key=lambda x: x.created_at)
                for activity in sorted_activities:
                    activity_node = tree_display.add_node(
                        str(activity), parent=issue_node
                    )

                    if isinstance(activity, Comment) and activity.attachments:
                        # Sorting attachments by their upload time within each activity
                        sorted_attachments = sorted(
                            activity.attachments, key=lambda x: x.uploaded_at
                        )
                        for attachment in sorted_attachments:
                            tree_display.add_node(str(attachment), parent=activity_node)

                # Sorting attachments by their upload time at the issue level
                sorted_issue_attachments = sorted(
                    issue.attachments, key=lambda x: x.uploaded_at
                )
                for attachment in sorted_issue_attachments:
                    tree_display.add_node(str(attachment), parent=issue_node)

        return tree_display.display()
