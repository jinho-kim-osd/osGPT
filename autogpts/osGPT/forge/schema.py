from __future__ import annotations

from typing import List, Optional
from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field
from .utils import humanize_time
from .tree_display import TreeStructureDisplay


class UserType(str, Enum):
    HUMAN = "Human"
    AGENT = "Agent"


class Role(str, Enum):
    ADMIN = "Administrator"
    MEMBER = "Member"
    VIEWER = "Viewer"


class User(BaseModel):
    public_name: str
    job_title: str
    department: Optional[str]
    organization: Optional[str]


class IssueType(str, Enum):
    EPIC = "Epic"
    TASK = "Task"
    STORY = "Story"
    BUG = "Bug"


class IssuePriority(str, Enum):
    HIGHEST = "Highest"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    LOWEST = "Lowest"


class Status(str, Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    REOPENED = "Reopened"
    CLOSED = "Closed"


class IssueLinkType(str, Enum):
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
    ATTACHMENT_UPDATE = "Attachment Update"
    ATTACHMENT_DELETION = "Attachment Deletion"
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


class Attachment(BaseModel):
    url: str
    filename: str
    filesize: int
    uploaded_at: datetime = Field(default_factory=datetime.now)

    def __str__(self):
        humanized_time = humanize_time(self.uploaded_at)
        return f"File: {self.filename}, Size: {self.filesize} bytes, " f"Uploaded on: {humanized_time}"

    def __hash__(self):
        return hash((self.filename, self.filesize, self.url))

    def __eq__(self, other):
        if isinstance(other, Attachment):
            return self.filename == other.filename and self.filesize == other.filesize and self.url == other.url
        return False


class Comment(Activity):
    type: ActivityType = ActivityType.COMMENT
    content: str
    attachments: List[Attachment] = Field(default_factory=list)

    def __str__(self):
        humanized_time = humanize_time(self.created_at)
        # truncated_comment = truncate_text(self.content, 200)
        return f"{self.created_by.public_name} added a Comment: '{self.content}'. {humanized_time}"

    def add_attachment(self, attachment: Attachment):
        """
        Add an attachment to the comment.
        """
        self.attachments.append(attachment)


class AttachmentUploadActivity(Activity):
    type: ActivityType = ActivityType.ATTACHMENT_UPLOAD
    attachments: List[Attachment]

    def __str__(self):
        humanized_time = humanize_time(self.created_at)
        attachment_info = ", ".join([attachment.filename for attachment in self.attachments])
        return f"{self.created_by.public_name} added attachments: {attachment_info}. {humanized_time}"


class AttachmentUpdateActivity(Activity):
    type: ActivityType = ActivityType.ATTACHMENT_UPDATE
    old_attachment: Attachment
    new_attachment: Attachment

    def __str__(self):
        humanized_time = humanize_time(self.created_at)
        return (
            f"{self.created_by.public_name} updated an Attachment: '{self.new_attachment.filename}'. "
            f"{humanized_time}"
        )


class AttachmentDeletionActivity(Activity):
    type: ActivityType = ActivityType.ATTACHMENT_DELETION
    attachment: Attachment

    def __str__(self):
        humanized_time = humanize_time(self.created_at)
        return (
            f"{self.created_by.public_name} deleted an Attachment: '{self.attachment.filename}'. " f"{humanized_time}"
        )


class AssignmentChangeActivity(Activity):
    type: ActivityType = ActivityType.ASSIGNMENT_CHANGE
    old_assignee: Optional[User]
    new_assignee: User

    def __str__(self) -> str:
        humanized_time = humanize_time(self.created_at)
        return (
            f"{self.created_by.public_name} changed the Assignee from "
            f"{self.old_assignee.public_name if self.old_assignee else 'None'} to "
            f"{self.new_assignee.public_name}. {humanized_time}"
        )


class StatusChangeActivity(Activity):
    type: ActivityType = ActivityType.STATUS_CHANGE
    old_status: Status
    new_status: Status

    def __str__(self):
        humanized_time = humanize_time(self.created_at)
        return (
            f"{self.created_by.public_name} changed the Status {self.old_status} → "
            f"{self.new_status}. {humanized_time}"
        )


class IssueCreationActivity(Activity):
    type: ActivityType = ActivityType.ISSUE_CREATION

    def __str__(self):
        humanized_time = humanize_time(self.created_at)
        return f"{self.created_by.public_name} created the Issue. {humanized_time}"


class IssueDeletionActivity(Activity):
    type: ActivityType = ActivityType.ISSUE_DELETION

    def __str__(self):
        humanized_time = humanize_time(self.created_at)
        return f"{self.created_by.public_name} delete the Issue. {humanized_time}"


class IssueLinkCreationActivity(Activity):
    type: ActivityType = ActivityType.ISSUE_LINK_CREATION
    link: IssueLink

    def __str__(self):
        humanized_time = humanize_time(self.created_at)
        return f"{self.created_by.public_name} created a link: {str(self.link)}. {humanized_time}"


class IssueLinkDeletionActivity(Activity):
    type: ActivityType = ActivityType.ISSUE_LINK_DELETION
    link: IssueLink

    def __str__(self):
        humanized_time = humanize_time(self.created_at)
        return f"{self.created_by.public_name} deleted a link: {str(self.link)}. {humanized_time}"


class Issue(BaseModel):
    id: int
    summary: str
    description: Optional[str]
    type: IssueType
    status: Status = Status.OPEN
    assignee: Optional[User]
    priority: Optional[IssuePriority]
    labels: List[str] = Field(default_factory=list)
    reporter: User
    parent_issue: Optional[Issue]
    child_issues: List[Issue] = Field(default_factory=list)
    links: List[IssueLink] = Field(default_factory=list)
    activities: List[Activity] = Field(default_factory=list)
    attachments: List[Attachment] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True

    def __str__(self):
        assignee_str = f", Assignee: {self.assignee.public_name}" if self.assignee else ", Assignee: None"
        return f"{self.type} Issue #{self.id}: {self.summary} (Status: {self.status}{assignee_str})"

    def add_activity(self, activity: Activity):
        self.activities.append(activity)

    def get_last_activity(self) -> Optional[Activity]:
        if self.activities:
            return self.activities[-1]
        return None

    def add_attachments(self, attachments: List[Attachment], created_by: User):
        new_attachments = []
        updated_attachments = []

        for attachment in attachments:
            existing_attachment = next((a for a in self.attachments if a.url == attachment.url), None)

            if existing_attachment:
                self.attachments.remove(existing_attachment)
                updated_attachments.append((existing_attachment, attachment))
            else:
                new_attachments.append(attachment)

            self.attachments.append(attachment)

        if new_attachments:
            upload_activity = AttachmentUploadActivity(created_by=created_by, attachments=new_attachments)
            self.add_activity(upload_activity)

        if updated_attachments:
            for old_attachment, new_attachment in updated_attachments:
                update_activity = AttachmentUpdateActivity(
                    created_by=created_by, old_attachment=old_attachment, new_attachment=new_attachment
                )
                self.add_activity(update_activity)

    def remove_attachment(self, attachment: Attachment, created_by: User):
        self.attachments.remove(attachment)
        activity = AttachmentDeletionActivity(created_by=created_by, attachment=attachment)
        self.add_activity(activity)

    def add_link(self, link_type: IssueLinkType, target_issue: Issue, created_by: User):
        link = IssueLink(type=link_type, source_issue=self, target_issue=target_issue)
        self.links.append(link)
        activity = IssueLinkCreationActivity(created_by=created_by, link=link)
        self.add_activity(activity)

    def remove_link(self, link: IssueLink, created_by: User):
        self.links.remove(link)
        activity = IssueLinkDeletionActivity(created_by=created_by, link=link)
        self.add_activity(activity)

    def change_status(self, new_status: Status, changed_by: User):
        if self.status != new_status:
            old_status = self.status
            self.status = new_status

            status_change_activity = StatusChangeActivity(
                old_status=old_status, new_status=new_status, created_by=changed_by
            )
            self.add_activity(status_change_activity)

    def display(self) -> str:
        tree_display = TreeStructureDisplay()

        issue_info = f"📋 {self.type} Issue #{self.id}: '{self.summary}' (Status: {self.status}, Assignee: {self.assignee.public_name if self.assignee else 'None'})"
        issue_node = tree_display.add_node(issue_info)

        if self.description:
            desc_node = tree_display.add_node(f"📄 Description:", parent=issue_node)
            for paragraph in self.description.split("\n"):
                if paragraph.strip():
                    tree_display.add_node(paragraph.strip(), parent=desc_node)

        # Add Parent Issue if exists
        # if self.parent_issue:
        #     parent_issue = self.parent_issue
        #     parent_issue_node = tree_display.add_node(
        #         "👪 Parent Issue:", parent=issue_node
        #     )
        #     parent_info = f"📋 {parent_issue.type} Issue #{parent_issue.id}: '{parent_issue.summary}' (Status: {parent_issue.status}, Assignee: {parent_issue.assignee.public_name if parent_issue.assignee else 'None'})"
        #     parent_node = tree_display.add_node(parent_info, parent=parent_issue_node)

        #     if self.parent_issue.description:
        #         parent_desc_node = tree_display.add_node(
        #             f"📄 Description:", parent=parent_node
        #         )
        #         for paragraph in self.parent_issue.description.split("\n"):
        #             if paragraph.strip():  # Ignore empty lines
        #                 tree_display.add_node(
        #                     paragraph.strip(), parent=parent_desc_node
        #                 )

        # Add Sub Issues if exist
        # if self.child_issues:
        #     child_issues_node = tree_display.add_node(
        #         "👶 Sub Issues:", parent=issue_node
        #     )
        #     for child_issue in self.child_issues:
        #         child_info = f"📋 {child_issue.type} Issue #{child_issue.id}: '{child_issue.summary}' (Status: {child_issue.status}, Assignee: {child_issue.assignee.public_name if child_issue.assignee else 'None'})"
        #         child_node = tree_display.add_node(child_info, parent=child_issues_node)

        #         if child_issue.description:
        #             child_desc_node = tree_display.add_node(
        #                 f"📄 Description:", parent=child_node
        #             )
        #             for paragraph in child_issue.description.split("\n"):
        #                 if paragraph.strip():
        #                     tree_display.add_node(
        #                         paragraph.strip(), parent=child_desc_node
        #                     )

        if self.links:
            linked_issues_node = tree_display.add_node("🔗 Linked Issues:", parent=issue_node)
            for link in self.links:
                link_info = f"Type: {link.type}, {link.target_issue}"
                tree_display.add_node(link_info, parent=linked_issues_node)

        if self.activities:
            activities_node = tree_display.add_node("📆 Activities:", parent=issue_node)
            for activity in sorted(self.activities, key=lambda x: x.created_at):
                activity_info = f"{activity}"
                activity_node = tree_display.add_node(activity_info, parent=activities_node)

                if isinstance(activity, Comment) and activity.attachments:
                    for attachment in sorted(activity.attachments, key=lambda x: x.uploaded_at):
                        attachment_info = f"📎 '{attachment.filename}' (Size: {attachment.filesize} bytes, Uploaded on: {humanize_time(attachment.uploaded_at)})"
                        tree_display.add_node(attachment_info, parent=activity_node)

        if self.attachments:
            attachments_node = tree_display.add_node("📎 Attachments:", parent=issue_node)
            for attachment in sorted(self.attachments, key=lambda x: x.uploaded_at):
                attachment_info = (
                    f"File: {attachment.filename}, Uploaded at: {attachment.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                tree_display.add_node(attachment_info, parent=attachments_node)

        return tree_display.display()


class Epic(Issue):
    type: IssueType = IssueType.EPIC


class IssueLink(BaseModel):
    type: IssueLinkType
    source_issue: Issue
    target_issue: Issue

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
            (t for t in self.transitions if t.name == transition_name and t.is_valid(issue)),
            None,
        )
        if transition:
            issue.status = transition.destination_status
            return True
        return False


class ProjectMember(BaseModel):
    user: User
    role: Role

    def __str__(self):
        return f"{self.user.public_name} (Job: {self.user.job_title})"


class Project(BaseModel):
    name: str
    key: str
    project_leader: User
    default_assignee: Optional[User]
    issues: List[Issue] = Field(default_factory=list)
    members: List[ProjectMember] = Field(default_factory=list)
    workflow: Workflow

    def __str__(self):
        return f"Project {self.name} (Key: {self.key}, Leader: {self.project_leader.public_name})"

    def reset(self):
        self.issues = []
        self.members = []

    def create_issue(
        self,
        type: IssueType,
        summary: str,
        reporter: User,
        description: Optional[str] = None,
        assignee: Optional[User] = None,
        parent_issue: Optional[Issue] = None,
    ) -> Issue:
        issue = Issue(
            id=len(self.issues) + 1,
            summary=summary,
            description=description,
            type=type,
            reporter=reporter,
            assignee=assignee,
            parent_issue=parent_issue,
        )
        self.add_issue(issue)

        activity = IssueCreationActivity(created_by=reporter)
        issue.add_activity(activity)
        return issue

    def add_issue(self, issue: Issue):
        self.issues.append(issue)

    def get_issue(self, issue_id: int) -> Issue:
        for issue in self.issues:
            if issue.id == issue_id:
                return issue
        raise ValueError(f"No issue found with ID {issue_id}")

    def get_member(self, public_name: str) -> ProjectMember:
        for member in self.members:
            if member.user.public_name == public_name:
                return member
        raise ValueError(f"No member found with user name {public_name}")

    def add_member(self, user: User, role: Role):
        member = ProjectMember(user=user, role=role)
        self.members.append(member)

    def apply_transition(self, issue: Issue, transition_name: str):
        if self.workflow.execute_transition(issue, transition_name):
            print(f"Transition '{transition_name}' applied to issue #{issue.id}. New status: {issue.status}")
        else:
            print(f"Failed to apply transition '{transition_name}' to issue #{issue.id}")

    def display(self, exclude: List[str] = None) -> str:
        if exclude is None:
            exclude = []

        tree_display = TreeStructureDisplay()
        project_node = tree_display.add_node(f"📁 {str(self)}")

        if "members" not in exclude and self.members:
            project_members_node = tree_display.add_node("👤 Members:", parent=project_node)
            for member in self.members:
                member_node = tree_display.add_node(str(member), parent=project_members_node)

        sorted_issues = sorted(self.issues, key=lambda x: x.id)
        for issue in sorted_issues:
            issue_info = f"📋 {issue.type} Issue #{issue.id}: {issue.summary} (Status: {issue.status}, Assignee: {issue.assignee.public_name if issue.assignee else 'None'})"
            issue_node = tree_display.add_node(issue_info, parent=project_node)

            if "description" not in exclude and issue.description:
                desc_node = tree_display.add_node(f"📄 Description:", parent=issue_node)
                for paragraph in issue.description.split("\n"):
                    if paragraph.strip():
                        tree_display.add_node(paragraph.strip(), parent=desc_node)

            if "linked_issues" not in exclude and issue.links:
                linked_issues_node = tree_display.add_node("🔗 Linked Issues:", parent=issue_node)
                for link in issue.links:
                    link_info = f"Type: {link.type}, {link.target_issue}"
                    tree_display.add_node(link_info, parent=linked_issues_node)

            if "activities" not in exclude and issue.activities:
                activities_node = tree_display.add_node("📆 Activities:", parent=issue_node)
                for activity in sorted(issue.activities, key=lambda x: x.created_at):
                    activity_info = f"{activity}"
                    activity_node = tree_display.add_node(activity_info, parent=activities_node)

                    if "attachments" not in exclude and isinstance(activity, Comment) and activity.attachments:
                        for attachment in sorted(activity.attachments, key=lambda x: x.uploaded_at):
                            attachment_info = f"📎 '{attachment.filename}' (Size: {attachment.filesize} bytes, Uploaded on: {humanize_time(attachment.uploaded_at)})"
                            tree_display.add_node(attachment_info, parent=activity_node)

            if "attachments" not in exclude and issue.attachments:
                attachments_node = tree_display.add_node("📎 Attachments:", parent=issue_node)
                for attachment in sorted(issue.attachments, key=lambda x: x.uploaded_at):
                    attachment_info = f"📎 '{attachment.filename}' (Size: {attachment.filesize} bytes, Uploaded on: {humanize_time(attachment.uploaded_at)})"
                    tree_display.add_node(attachment_info, parent=attachments_node)

        return tree_display.display()
