from typing import Optional

from .sdk import AgentDB, ForgeLogger, NotFoundError, Base
from sqlalchemy.exc import SQLAlchemyError

import datetime
from sqlalchemy import (
    Column,
    DateTime,
    String,
)
import uuid

LOG = ForgeLogger(__name__)


class ChatModel(Base):
    __tablename__ = "chat"
    msg_id = Column(String, primary_key=True, index=True)
    task_id = Column(String)
    step_id = Column(String, nullable=True)
    role = Column(String)
    content = Column(String)
    sender = Column(String, nullable=True)
    recipient = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    modified_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )


class ActionModel(Base):
    __tablename__ = "action"
    action_id = Column(String, primary_key=True, index=True)
    task_id = Column(String)
    step_id = Column(String, nullable=True)
    name = Column(String)
    args = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    modified_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )


class ForgeDatabase(AgentDB):
    async def add_chat_message(
        self,
        task_id,
        role,
        content,
        step_id: Optional[str] = None,
        sender: Optional[str] = None,
        recipient: Optional[str] = None,
    ):
        if self.debug_enabled:
            LOG.debug("Creating new task")
        try:
            with self.Session() as session:
                mew_msg = ChatModel(
                    msg_id=str(uuid.uuid4()),
                    task_id=task_id,
                    step_id=step_id,
                    role=role,
                    content=content,
                    sender=sender,
                    recipient=recipient,
                )
                session.add(mew_msg)
                session.commit()
                session.refresh(mew_msg)
                if self.debug_enabled:
                    LOG.debug(
                        f"Created new Chat message with task_id: {mew_msg.msg_id}"
                    )
                return mew_msg
        except SQLAlchemyError as e:
            LOG.error(f"SQLAlchemy error while creating task: {e}")
            raise
        except NotFoundError as e:
            raise
        except Exception as e:
            LOG.error(f"Unexpected error while creating task: {e}")
            raise

    async def get_chat_history(self, task_id: str, step_id: Optional[str] = None):
        if self.debug_enabled:
            LOG.debug(
                f"Getting chat history with task_id: {task_id}, step_id: {step_id}"
            )
        try:
            with self.Session() as session:
                query = session.query(ChatModel).filter(ChatModel.task_id == task_id)

                if step_id is not None:
                    query = query.filter(ChatModel.step_id == step_id)

                messages = query.order_by(ChatModel.created_at).all()

                if messages:
                    return [{"role": m.role, "content": m.content} for m in messages]
                else:
                    LOG.info(
                        f"Chat history not found with task_id: {task_id}, step_id: {step_id}"
                    )
                    return []
        except SQLAlchemyError as e:
            LOG.error(f"SQLAlchemy error while getting chat history: {e}")
            raise
        except NotFoundError as e:
            raise
        except Exception as e:
            LOG.error(f"Unexpected error while getting chat history: {e}")
            raise

    async def create_action(self, task_id, name, args):
        try:
            with self.Session() as session:
                new_action = ActionModel(
                    action_id=str(uuid.uuid4()),
                    task_id=task_id,
                    name=name,
                    args=str(args),
                )
                session.add(new_action)
                session.commit()
                session.refresh(new_action)
                if self.debug_enabled:
                    LOG.debug(
                        f"Created new Action with task_id: {new_action.action_id}"
                    )
                return new_action
        except SQLAlchemyError as e:
            LOG.error(f"SQLAlchemy error while creating action: {e}")
            raise
        except NotFoundError as e:
            raise
        except Exception as e:
            LOG.error(f"Unexpected error while creating action: {e}")
            raise

    async def get_action_history(self, task_id):
        if self.debug_enabled:
            LOG.debug(f"Getting action history with task_id: {task_id}")
        try:
            with self.Session() as session:
                if actions := (
                    session.query(ActionModel)
                    .filter(ActionModel.task_id == task_id)
                    .order_by(ActionModel.created_at)
                    .all()
                ):
                    return [{"name": a.name, "args": a.args} for a in actions]

                else:
                    LOG.error(f"Action history not found with task_id: {task_id}")
                    raise NotFoundError("Action history not found")
        except SQLAlchemyError as e:
            LOG.error(f"SQLAlchemy error while getting action history: {e}")
            raise
        except NotFoundError as e:
            raise
        except Exception as e:
            LOG.error(f"Unexpected error while getting action history: {e}")
            raise
