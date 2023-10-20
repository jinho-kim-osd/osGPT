from __future__ import annotations

from abc import abstractmethod
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field
from .utils import humanize_time, truncate_text
from .display import TreeStructureDisplay


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


class Status(str, Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    REOPENED = "Reopened"
    CLOSED = "Closed"


class IssueLinkType(str, Enum):
    """
    Enumeration of potential issue link types.
    """

    BLOCKS = "blocks"
    IS_BLOCKED_BY = "is blocked by"
    CLONES = "clones"
    IS_CLONED_BY = "is cloned by"
    DUPLICATES = "duplicates"
    IS_DUPLICATED_BY = "is duplicated by"
    RELATES_TO = "relates to"


class ActivityType(str, Enum):
    COMMENT = "Comment"
    ATTACHMENT_UPLOAD = "Attachment Upload"
    ASSIGNMENT_CHANGE = "Assignment Change"
    STATUS_CHANGE = "Status Change"
    ISSUE_CREATION = "Issue Creation"
    ISSUE_DELETION = "Issue Deletion"
    ISSUE_LINK_CREATION = "Issue Link Creation"
    ISSUE_LINK_DELETION = "Issue Link Deletion"


class Activity(BaseModel):
    type: ActivityType
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: User

    class Config:
        arbitrary_types_allowed = True


class Attachment(BaseModel):
    """
    Represents a file attachment associated with a comment.
    """

    url: str
    filename: str
    filesize: int
    uploaded_at: datetime = Field(default_factory=datetime.now)

    def __str__(self):
        humanized_time = humanize_time(self.uploaded_at)
        return (
            f"File: {self.filename}, Size: {self.filesize} bytes, "
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


class IssueLinkCreationActivity(Activity):
    type: ActivityType = ActivityType.ISSUE_LINK_CREATION
    link: IssueLink

    def __str__(self):
        humanized_time = humanize_time(self.created_at)
        return (
            f"{self.created_by.name} created a link: {str(self.link)}. {humanized_time}"
        )


class IssueLinkDeletionActivity(Activity):
    type: ActivityType = ActivityType.ISSUE_LINK_DELETION
    link: IssueLink

    def __str__(self):
        humanized_time = humanize_time(self.created_at)
        return (
            f"{self.created_by.name} deleted a link: {str(self.link)}. {humanized_time}"
        )


class Issue(BaseModel):
    id: int
    summary: str
    description: Optional[str]
    type: IssueType
    status: Status = Status.OPEN
    assignee: Optional[User]
    # labels: List[str] = Field(default_factory=list)
    # start_date: Optional[datetime] = Field(None)
    # due_date: Optional[datetime] = Field(None)
    reporter: User
    parent_issue: Optional[Issue]
    child_issues: List[Issue] = Field(default_factory=list)
    links: List[IssueLink] = Field(default_factory=list)
    activities: List[Activity] = Field(default_factory=list)
    attachments: List[Attachment] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True

    def __str__(self):
        assignee_str = (
            f", Assignee: {self.assignee.name}" if self.assignee else ", Assignee: None"
        )
        return f"{self.type} Issue #{self.id}: {self.summary} (Status: {self.status}{assignee_str})"

    def add_activity(self, activity: Activity):
        self.activities.append(activity)

    def add_attachment(self, attachment: Attachment):  # And added this method
        self.attachments.append(attachment)

    def add_link(self, link_type: IssueLinkType, target_issue: Issue):
        """
        Add a link between the current issue and another issue.
        """
        link = IssueLink(type=link_type, source_issue=self, target_issue=target_issue)
        self.links.append(link)

    def display(self) -> str:
        tree_display = TreeStructureDisplay()

        issue_info = f"📋 {self.type} Issue #{self.id}: '{self.summary}' (Status: {self.status}, Assignee: {self.assignee.name if self.assignee else 'None'})"
        issue_node = tree_display.add_node(issue_info)

        if self.description:
            desc_node = tree_display.add_node(f"📄 Description:", parent=issue_node)
            for paragraph in self.description.split("\n"):
                if paragraph.strip():
                    tree_display.add_node(paragraph.strip(), parent=desc_node)

        # Add Parent Issue if exists
        if self.parent_issue:
            parent_issue = self.parent_issue
            parent_issue_node = tree_display.add_node(
                "👪 Parent Issue:", parent=issue_node
            )
            parent_info = f"📋 {parent_issue.type} Issue #{parent_issue.id}: '{parent_issue.summary}' (Status: {parent_issue.status}, Assignee: {parent_issue.assignee.name if parent_issue.assignee else 'None'})"
            parent_node = tree_display.add_node(parent_info, parent=parent_issue_node)

            if self.parent_issue.description:
                parent_desc_node = tree_display.add_node(
                    f"📄 Description:", parent=parent_node
                )
                for paragraph in self.parent_issue.description.split("\n"):
                    if paragraph.strip():  # Ignore empty lines
                        tree_display.add_node(
                            paragraph.strip(), parent=parent_desc_node
                        )

        # Add Sub Issues if exist
        if self.child_issues:
            child_issues_node = tree_display.add_node(
                "👶 Sub Issues:", parent=issue_node
            )
            for child_issue in self.child_issues:
                child_info = f"📋 {child_issue.type} Issue #{child_issue.id}: '{child_issue.summary}' (Status: {child_issue.status}, Assignee: {child_issue.assignee.name if child_issue.assignee else 'None'})"
                child_node = tree_display.add_node(child_info, parent=child_issues_node)

                if child_issue.description:
                    child_desc_node = tree_display.add_node(
                        f"📄 Description:", parent=child_node
                    )
                    for paragraph in child_issue.description.split("\n"):
                        if paragraph.strip():
                            tree_display.add_node(
                                paragraph.strip(), parent=child_desc_node
                            )

        if self.links:
            linked_issues_node = tree_display.add_node(
                "🔗 Linked Issues:", parent=issue_node
            )
            for link in self.links:
                link_info = f"Type: {link.type}, {link.target_issue}"
                tree_display.add_node(link_info, parent=linked_issues_node)

        if self.activities:
            activities_node = tree_display.add_node("📆 Activities:", parent=issue_node)
            for activity in sorted(self.activities, key=lambda x: x.created_at):
                activity_info = f"{activity}"
                activity_node = tree_display.add_node(
                    activity_info, parent=activities_node
                )

                if isinstance(activity, Comment) and activity.attachments:
                    for attachment in sorted(
                        activity.attachments, key=lambda x: x.uploaded_at
                    ):
                        attachment_info = f"📎 '{attachment.filename}' (Size: {attachment.filesize} bytes, Uploaded on: {humanize_time(attachment.uploaded_at)})"
                        tree_display.add_node(attachment_info, parent=activity_node)

        if self.attachments:
            attachments_node = tree_display.add_node(
                "📎 Attachments:", parent=issue_node
            )
            for attachment in sorted(self.attachments, key=lambda x: x.uploaded_at):
                attachment_info = f"File: {attachment.filename}, Uploaded at: {attachment.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')}"
                tree_display.add_node(attachment_info, parent=attachments_node)

        return tree_display.display()


class Epic(Issue):
    type: IssueType = IssueType.EPIC


class IssueLink(BaseModel):
    """
    Represents a link between two issues.
    """

    type: IssueLinkType
    source_issue: Issue
    target_issue: Issue

    class Config:
        arbitrary_types_allowed = True

    def __str__(self):
        return f"{self.source_issue.id} {self.type.value} {self.target_issue.id}"


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


class Project(BaseModel):
    name: str
    key: str
    project_leader: User
    default_assignee: Optional[User]
    issues: List[Issue] = Field(default_factory=list)
    workflow: Workflow

    class Config:
        arbitrary_types_allowed = True

    def __str__(self):
        return (
            f"Project {self.name} (Key: {self.key}, Leader: {self.project_leader.name})"
        )

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
        project_node = tree_display.add_node(f"📁 {str(self)}")

        # Sorting issues by their ID in ascending order
        sorted_issues = sorted(self.issues, key=lambda x: x.id)

        for issue in sorted_issues:
            issue_info = f"📋 {issue.type} Issue #{issue.id}: {issue.summary} (Status: {issue.status}, Assignee: {issue.assignee.name if issue.assignee else 'None'})"
            issue_node = tree_display.add_node(issue_info, parent=project_node)

            if issue.description:
                desc_node = tree_display.add_node(f"📄 Description:", parent=issue_node)
                for paragraph in issue.description.split("\n"):
                    if paragraph.strip():
                        tree_display.add_node(paragraph.strip(), parent=desc_node)

            if issue.parent_issue:
                parent_issue = issue.parent_issue
                parent_issue_node = tree_display.add_node(
                    "👪 Parent Issue:", parent=issue_node
                )
                parent_info = f"📋 {parent_issue.type} Issue #{parent_issue.id}: '{parent_issue.summary}' (Status: {parent_issue.status}, Assignee: {parent_issue.assignee.name if parent_issue.assignee else 'None'})"
                parent_node = tree_display.add_node(
                    parent_info, parent=parent_issue_node
                )

            if issue.links:
                linked_issues_node = tree_display.add_node(
                    "🔗 Linked Issues:", parent=issue_node
                )
                for link in issue.links:
                    link_info = f"Type: {link.type}, {link.target_issue}"
                    tree_display.add_node(link_info, parent=linked_issues_node)

            if issue.activities:
                activities_node = tree_display.add_node(
                    "📆 Activities:", parent=issue_node
                )
                for activity in sorted(issue.activities, key=lambda x: x.created_at):
                    activity_info = f"{activity}"
                    activity_node = tree_display.add_node(
                        activity_info, parent=activities_node
                    )

                    if isinstance(activity, Comment) and activity.attachments:
                        for attachment in sorted(
                            activity.attachments, key=lambda x: x.uploaded_at
                        ):
                            attachment_info = f"📎 '{attachment.filename}' (Size: {attachment.filesize} bytes, Uploaded on: {humanize_time(attachment.uploaded_at)})"
                            tree_display.add_node(attachment_info, parent=activity_node)

            if issue.attachments:
                attachments_node = tree_display.add_node(
                    "📎 Attachments:", parent=issue_node
                )
                for attachment in sorted(
                    issue.attachments, key=lambda x: x.uploaded_at
                ):
                    attachment_info = f"File: {attachment.filename}, Uploaded at: {attachment.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')}"
                    tree_display.add_node(attachment_info, parent=attachments_node)

        return tree_display.display()


class WorkspaceMember(BaseModel):
    user: User
    workspace_role: str
    additional_info: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"

    def __str__(self):
        return f"{self.user.name} (Role: {self.workspace_role})"

    def add_info(self, key: str, value: Any):
        self.additional_info[key] = value


class Workspace(BaseModel):
    name: str
    projects: List[Project] = Field(default_factory=list)
    members: List[WorkspaceMember] = Field(default_factory=list)

    def __str__(self):
        return f"Workspace: {self.name}"

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
        workspace_node = tree_display.add_node(f"🌐 {str(self)}")

        for member in self.members:
            tree_display.add_node(str(member), parent=workspace_node)

        for project in self.projects:
            project_node = tree_display.add_node(
                f"📁 {str(project)}", parent=workspace_node
            )

            # Sorting issues by their ID in ascending order
            sorted_issues = sorted(project.issues, key=lambda x: x.id)

            for issue in sorted_issues:
                issue_info = f"📋 {issue.type} Issue #{issue.id}: {issue.summary}"
                # issue_info = f"📋 {issue.type} Issue #{issue.id}: {issue.summary} (Status: {issue.status}, Assignee: {issue.assignee.name if issue.assignee else 'None'})"

                issue_node = tree_display.add_node(issue_info, parent=project_node)

                # # Sorting activities by their creation time within each issue
                # sorted_activities = sorted(issue.activities, key=lambda x: x.created_at)
                # for activity in sorted_activities:
                #     activity_node = tree_display.add_node(
                #         str(activity), parent=issue_node
                #     )

                #     if isinstance(activity, Comment) and activity.attachments:
                #         # Sorting attachments by their upload time within each activity
                #         sorted_attachments = sorted(
                #             activity.attachments, key=lambda x: x.uploaded_at
                #         )
                #         for attachment in sorted_attachments:
                #             tree_display.add_node(
                #                 f"📎 {str(attachment)}", parent=activity_node
                #             )

                # # Sorting attachments by their upload time at the issue level
                # sorted_issue_attachments = sorted(
                #     issue.attachments, key=lambda x: x.uploaded_at
                # )
                # for attachment in sorted_issue_attachments:
                #     tree_display.add_node(f"📎 {str(attachment)}", parent=issue_node)

        return tree_display.display()
