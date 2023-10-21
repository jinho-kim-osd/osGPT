from __future__ import annotations

from typing import Optional, List
import datetime
import uuid

from sqlalchemy import (
    Column,
    DateTime,
    String,
    JSON,
    Integer,
    Enum,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.exc import SQLAlchemyError

from forge.sdk import AgentDB, ForgeLogger, NotFoundError, Base

# from .message import Message
# from .profile_agent import JiraAgent
# from .workspace import Workspace

LOG = ForgeLogger(__name__)


# class WorkspaceModel(Base):
#     __tablename__ = "workspaces"
#     workspace_id = Column(String, primary_key=True, index=True)
#     name = Column(String)
#     base_path = Column(String, nullable=True)

#     # users = relationship("UserModel", back_populates="workspace")
#     # projects = relationship("ProjectModel", back_populates="workspace")

#     created_at = Column(DateTime, default=datetime.datetime.utcnow)
#     modified_at = Column(
#         DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
#     )


# class ProjectModel(Base):
#     __tablename__ = "projects"
#     project_id = Column(String, primary_key=True, index=True)
#     workspace_id = Column(String, ForeignKey("workspaces.workspace_id"))
#     name = Column(String)
#     key = Column(String)
#     project_leader_id = Column(String, ForeignKey("users.user_id"))
#     default_assignee_id = Column(String, ForeignKey("users.user_id"))
#     workflow_id = Column(String, ForeignKey("workflows.workflow_id"))
#     created_at = Column(DateTime, default=datetime.datetime.utcnow)
#     modified_at = Column(
#         DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
#     )

#     workspace = relationship("WorkspaceModel", back_populates="projects")
#     project_leader = relationship("UserModel", foreign_keys=[project_leader_id])
#     default_assignee = relationship("UserModel", foreign_keys=[default_assignee_id])


# class IssueModel(Base):
#     __tablename__ = "issues"
#     issue_id = Column(Integer, primary_key=True, index=True)
#     summary = Column(String)
#     description = Column(String, nullable=True)
#     type = Column(Enum(IssueType))
#     status = Column(Enum(Status), default=Status.OPEN)
#     assignee_id = Column(String, ForeignKey("users.user_id"))
#     parent_issue_id = Column(Integer, ForeignKey("issues.issue_id"), nullable=True)
#     project_id = Column(String, ForeignKey("projects.project_id"))
#     created_at = Column(DateTime, default=datetime.datetime.utcnow)
#     modified_at = Column(
#         DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
#     )

#     assignee = relationship("UserModel", foreign_keys=[assignee_id])


# class ActivityModel(Base):
#     __tablename__ = "activities"
#     activity_id = Column(String, primary_key=True, index=True)
#     type = Column(Enum(ActivityType))
#     created_at = Column(DateTime, default=datetime.datetime.utcnow)
#     user_id = Column(String, ForeignKey("users.user_id"))

#     user = relationship("UserModel", back_populates="activities")


# class CommentModel(ActivityModel):
#     __tablename__ = "comments"
#     comment_id = Column(String, ForeignKey("activities.activity_id"), primary_key=True)
#     content = Column(String)
#     attachments = relationship("AttachmentModel", back_populates="comment")


# class WorkflowModel(Base):
#     __tablename__ = "workflows"
#     workflow_id = Column(String, primary_key=True, index=True)
#     name = Column(String)
#     created_at = Column(DateTime, default=datetime.datetime.utcnow)
#     modified_at = Column(
#         DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
#     )


# class AttachmentModel(Base):
#     __tablename__ = "attachments"
#     attachment_id = Column(String, primary_key=True, index=True)
#     url = Column(String)
#     filename = Column(String)
#     filesize = Column(Integer)
#     uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)
#     comment_id = Column(String, ForeignKey("comments.comment_id"))

#     comment = relationship("CommentModel", back_populates="attachments")


# class UserModel(Base):
#     __tablename__ = "users"
#     user_id = Column(String, primary_key=True, index=True)
#     workspace_id = Column(String, ForeignKey("workspaces.workspace_id"))
#     name = Column(String)
#     role = Column(String)
#     ability_names = Column(JSON)
#     system_prompt = Column(String, nullable=True)
#     created_at = Column(DateTime, default=datetime.datetime.utcnow)
#     modified_at = Column(
#         DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
#     )

#     workspace = relationship("WorkspaceModel", back_populates="users")
#     activities = relationship("ActivityModel", back_populates="user")


# class MessageModel(Base):
#     __tablename__ = "messages"
#     message_id = Column(String, primary_key=True, index=True)
#     task_id = Column(String)
#     step_id = Column(String, nullable=True)
#     content = Column(String)
#     sender_id = Column(String, nullable=True)
#     recipient_id = Column(String, nullable=True)
#     created_at = Column(DateTime, default=datetime.datetime.utcnow)
#     modified_at = Column(
#         DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
#     )


# def convert_to_workspace(workspace_model: WorkspaceModel) -> LocalWorkspace:
#     return LocalWorkspace(
#         workspace_id=workspace_model.workspace_id,
#         name=workspace_model.name,
#         base_path=workspace_model.base_path,
#     )


# def convert_to_user(user_model: UserModel) -> User:
#     return User(
#         message_id=user_model.message_id,
#         content=user_model.content,
#         sender_id=user_model.sender_id,
#         recipient_id=user_model.recipient_id,
#         created_at=user_model.created_at,
#         modified_at=user_model.modified_at,
#     )


# def convert_to_issue(issue_model: IssueModel) -> Issue:
#     return Issue(
#         id=issue_model.issue_id,
#         summary=issue_model.summary,
#         description=issue_model.description,
#         type=issue_model.type,
#         status=issue_model.status,
#         assignee=convert_to_user(issue_model.assignee),
#         created_at=issue_model.created_at,
#         modified_at=issue_model.modified_at,
#     )


# def convert_to_message(message_model: MessageModel) -> Message:
#     return Message(
#         message_id=message_model.message_id,
#         content=message_model.content,
#         sender_id=message_model.sender_id,
#         recipient_id=message_model.recipient_id,
#         created_at=message_model.created_at,
#         modified_at=message_model.modified_at,
#     )


class ForgeDatabase(AgentDB):
    ...


#     def create_workspace(
#         self,
#         name: str,
#         base_path: Optional[str] = None,
#     ) -> WorkspaceModel:
#         with self.Session() as session:
#             new_workspace = WorkspaceModel(
#                 workspace_id=str(uuid.uuid4()),
#                 name=name,
#                 base_path=base_path,
#             )
#             session.add(new_workspace)
#             session.commit()
#             session.refresh(new_workspace)
#             return convert_to_workspace(new_workspace)

#     def get_workspace(self, workspace_id: str) -> Optional[LocalWorkspace]:
#         with self.Session() as session:
#             workspace = (
#                 session.query(WorkspaceModel)
#                 .filter_by(workspace_id=workspace_id)
#                 .first()
#             )
#             if workspace:
#                 return convert_to_workspace(workspace)
#             return None

# async def add_chat_message(
#     self,
#     task_id,
#     content,
#     step_id: Optional[str] = None,
#     sender_id: Optional[str] = None,
#     recipient_id: Optional[str] = None,
# ) -> MessageModel:
#     if self.debug_enabled:
#         LOG.debug("Creating new task")
#     try:
#         with self.Session() as session:
#             mew_msg = MessageModel(
#                 message_id=str(uuid.uuid4()),
#                 task_id=task_id,
#                 step_id=step_id,
#                 content=content,
#                 sender_id=sender_id,
#                 recipient_id=recipient_id,
#             )
#             session.add(mew_msg)
#             session.commit()
#             session.refresh(mew_msg)
#             if self.debug_enabled:
#                 LOG.debug(
#                     f"Created new Chat message with task_id: {mew_msg.message_id}"
#                 )
#             return mew_msg
#     except SQLAlchemyError as e:
#         LOG.error(f"SQLAlchemy error while creating task: {e}")
#         raise
#     except NotFoundError as e:
#         raise
#     except Exception as e:
#         LOG.error(f"Unexpected error while creating task: {e}")
#         raise

# async def get_chat_history(
#     self, task_id: str, step_id: Optional[str] = None
# ) -> List[Message]:
#     if self.debug_enabled:
#         LOG.debug(
#             f"Getting chat history with task_id: {task_id}, step_id: {step_id}"
#         )
#     try:
#         with self.Session() as session:
#             query = session.query(MessageModel).filter(
#                 MessageModel.task_id == task_id
#             )

#             if step_id is not None:
#                 query = query.filter(MessageModel.step_id == step_id)

#             messages = query.order_by(MessageModel.created_at).all()

#             if messages:
#                 return [
#                     Message(
#                         content=m.content,
#                         sender_id=m.sender_id,
#                         recipient_id=m.recipient_id,
#                     )
#                     for m in messages
#                 ]
#             else:
#                 LOG.info(
#                     f"Chat history not found with task_id: {task_id}, step_id: {step_id}"
#                 )
#                 return []
#     except SQLAlchemyError as e:
#         LOG.error(f"SQLAlchemy error while getting chat history: {e}")
#         raise
#     except NotFoundError as e:
#         raise
#     except Exception as e:
#         LOG.error(f"Unexpected error while getting chat history: {e}")
#         raise

# async def get_user(self, user_id: str) -> User:
#     """Get a task by its id"""
#     if self.debug_enabled:
#         LOG.debug(f"Getting user with user_id: {user_id}")
#     try:
#         with self.Session() as session:
#             if user_obj := (
#                 session.query(UserModel).filter_by(user_id=user_id).first()
#             ):
#                 return convert_to_user(user_obj, self.debug_enabled)
#             else:
#                 LOG.error(f"User not found with user_id: {user_id}")
#                 raise NotFoundError("User not found")
#     except SQLAlchemyError as e:
#         LOG.error(f"SQLAlchemy error while getting task: {e}")
#         raise
#     except NotFoundError as e:
#         raise
#     except Exception as e:
#         LOG.error(f"Unexpected error while getting task: {e}")
#         raise

# async def add_issue(
#     self,
#     project_id: str,
#     summary: str,
#     description: Optional[str],
#     type: IssueType,
#     assignee_id: str,
# ) -> IssueModel:
#     try:
#         with self.Session() as session:
#             new_issue = IssueModel(
#                 project_id=project_id,
#                 summary=summary,
#                 description=description,
#                 type=type,
#                 assignee_id=assignee_id,
#             )
#             session.add(new_issue)
#             session.commit()
#             session.refresh(new_issue)
#             return new_issue
#     except SQLAlchemyError as e:
#         LOG.error(f"SQLAlchemy error while creating issue: {e}")
#         raise
#     except Exception as e:
#         LOG.error(f"Unexpected error while creating issue: {e}")
#         raise
