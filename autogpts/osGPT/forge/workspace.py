from __future__ import annotations
from datetime import datetime
from typing import List, Dict, Any

from forge.sdk import Workspace as WorkspaceService
from .schema import Comment, User, Workspace, Attachment


class CollaborationWorkspace(Workspace):
    service: WorkspaceService

    class Config:
        arbitrary_types_allowed = True

    def read(self, task_id: str, path: str):
        return self.service.read(task_id, path)

    def write(self, task_id: str, path: str, data: bytes):
        return self.service.write(task_id, path, data)

    def list_attachments(self, task_id: str, path: str) -> List[Attachment]:
        base_path = self.service.base_path / task_id / path
        base = self.service._resolve_path(task_id, base_path)
        attachments = []

        if not base.exists() or not base.is_dir():
            return attachments

        for file in base.iterdir():
            if file.is_file():
                attachments.append(
                    Attachment(
                        filename=file.name,
                        filesize=file.stat().st_size,
                        url=str(file.relative_to(self.service.base_path / task_id)),
                    )
                )
        return attachments

    def display_structure(self) -> str:
        structure = f"{self}\n"

        for member in self.members:
            structure += f"  {member}\n"

        for project in self.projects:
            structure += f"{project}\n"

            for issue in project.issues:
                structure += f"  {issue}\n"

                for activity in issue.activities:
                    structure += f"    {activity}\n"

                if issue.attachments:
                    structure += "    Attachments:\n"
                    for attachment in issue.attachments:
                        structure += f"      {attachment}\n"

        return structure

    # def display_structure(self) -> str:
    #     """
    #     Display the structure of the workspace in a tree format including projects, issues, users, and comment attachments.
    #     """
    #     structure = f"🌐 Workspace: {self.name}\n"

    #     for member in self.members:
    #         structure += f"{MINIMUM_INDENT}👤 User: {member.user.name} (Role: {member.workspace_role})\n"

    #     for project in self.projects:
    #         structure += f"{MINIMUM_INDENT}📁 Project: {project.name} (Key: {project.key}, Leader: {project.project_leader.name})\n"

    #         if project.issues:
    #             structure += f"{MINIMUM_INDENT*2}📋 Issues:\n"

    #         for issue in project.issues:
    #             structure += f"{MINIMUM_INDENT*3}#{issue.id} {issue.summary} (Type: {issue.type}, Status: {issue.status}, Assignee: {issue.assignee.name})\n"

    #             if issue.activities:
    #                 structure += f"{MINIMUM_INDENT*4}🗨 Activities:\n"

    #             for activity in issue.activities:
    #                 if isinstance(activity, Comment):
    #                     structure += f"{MINIMUM_INDENT*5}• {activity.created_by.name} [{activity.created_at.strftime('%Y-%m-%d %H:%M:%S')}]: {activity.content}\n"

    #                     if activity.attachments:
    #                         structure += (
    #                             f"{MINIMUM_INDENT*6}📎 Attachments in Comment:\n"
    #                         )

    #                     for attachment in activity.attachments:
    #                         structure += f"{MINIMUM_INDENT*7}• File: {attachment.filename}, Size: {attachment.filesize} bytes, Uploaded on: {attachment.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')}\n"

    #             if issue.attachments:
    #                 structure += f"{MINIMUM_INDENT*4}📎 Attachments:\n"

    #             for attachment in issue.attachments:
    #                 structure += f"{MINIMUM_INDENT*5}• File: {attachment.filename}, Size: {attachment.filesize} bytes, Uploaded on: {attachment.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')}\n"

    #     return structure
