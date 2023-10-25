from typing import Optional, List

from pydantic import BaseModel, Field

from fastapi import APIRouter, Request

from forge.sdk.forge_log import ForgeLogger

from ..schema import (
    Project,
    Issue,
    Attachment,
    Comment,
    Activity,
    ProjectMember,
    IssueType,
    User,
    Status,
    IssuePriority,
)

jira_router = APIRouter()


LOG = ForgeLogger(__name__)


@jira_router.post("/project", tags=["project"])
async def create_project(request: Request, project_request: Project) -> Project:
    agent = request["agent"]

    project = await agent.workspace.create_project(**project_request.dict(exclude_none=True))

    return project


@jira_router.get("/project/{project_key}", tags=["project"])
async def get_project(request: Request, project_key: str) -> str:
    agent = request["agent"]

    project = agent.workspace.get_project(project_key)

    return project.key


@jira_router.get("/project", tags=["project"])
async def list_projects(request: Request) -> List[str]:  # List[Project]:
    # print([project.dict() for project in workspace.projects])

    return ["hi"]


@jira_router.post("/project/{project_key}/issues", tags=["issue"])
async def create_issue(request: Request, issue_request: Issue, project_key: str) -> Issue:
    agent = request["agent"]

    project = agent.workspace.get_project(project_key)

    issue = await project.create_issue(**issue_request.dict(exclude_none=True))

    return issue


@jira_router.get("/project/{project_key}/issues/{issue_id}", tags=["issue"])
async def get_issue(request: Request, project_key: str, issue_id: int) -> Issue:
    agent = request["agent"]

    project = agent.workspace.get_project(project_key)

    issue = project.get_issue(issue_id)

    return issue


class IssueUpdate(BaseModel):
    summary: Optional[str]

    description: Optional[str]

    status: Optional[Status] = Status.OPEN

    assignee: Optional[User]

    priority: Optional[IssuePriority]

    parent_issue_id: Optional[int]

    child_issue_ids: Optional[List[int]] = Field(default_factory=list)

    attachments: Optional[List[Attachment]] = Field(default_factory=list)


@jira_router.put("/project/{project_key}/issues/{issue_id}", tags=["issue"])
async def update_issue(request: Request, project_key: str, issue_id: int, issue_update: IssueUpdate) -> Issue:
    agent = request["agent"]

    project = agent.workspace.get_project(project_key)

    issue = project.get_issue(issue_id)

    if issue_update.summary is not None:
        issue.summary = issue_update.summary

    if issue_update.description is not None:
        issue.description = issue_update.description

    if issue_update.status is not None:
        issue.status = issue_update.status

    if issue_update.assignee is not None:
        issue.assignee = issue_update.assignee

    if issue_update.priority is not None:
        issue.priority = issue_update.priority

    if issue_update.parent_issue_id is not None:
        issue.parent_issue_id = issue_update.parent_issue_id

    if issue_update.child_issue_ids:
        issue.child_issue_ids.extend(issue_update.child_issue_ids)

    if issue_update.attachments:
        issue.attachments.extend(issue_update.attachments)

    return issue


@jira_router.get("/project/{project_key}/issues", tags=["issue"])
async def list_issues(request: Request, project_key: str) -> List[Issue]:
    agent = request["agent"]

    project = agent.workspace.get_project(project_key)

    return project.issues


@jira_router.get("/project/{project_key}/issues/{issue_id}/activities", tags=["activity"])
async def list_activities(request: Request, project_key: str, issue_id: int) -> List[Activity]:
    agent = request["agent"]

    project = agent.workspace.get_project(project_key)

    issue = project.get_issue(issue_id)

    return issue.activities


@jira_router.get("/project/{project_key}/members", tags=["member"])
async def list_members(request: Request, project_key: str) -> List[ProjectMember]:
    agent = request["agent"]

    project = agent.workspace.get_project(project_key)

    return project.members


@jira_router.post("/project/{project_key}/issues/{issue_id}/activities/comments", tags=["activity"])
async def add_comment(request: Request, project_key: str, issue_id: int, comment_request: Comment) -> Comment:
    agent = request["agent"]

    project = agent.workspace.get_project(project_key)

    issue = project.get_issue(issue_id)

    issue.activities.append(comment_request)

    return comment_request
