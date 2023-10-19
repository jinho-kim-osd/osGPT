from __future__ import annotations
from pathlib import Path
from typing import List

from forge.sdk import Workspace as WorkspaceService
from .schema import Workspace, Attachment


class CollaborationWorkspace(Workspace):
    service: WorkspaceService

    class Config:
        arbitrary_types_allowed = True

    @property
    def base_path(self) -> Path:
        return self.service.base_path

    def read(self, task_id: str, path: str):
        return self.service.read(task_id, path)

    def write(self, task_id: str, path: str, data: bytes):
        return self.service.write(task_id, path, data)

    def read_relative_path(self, path: str) -> bytes:
        with open(self._resolve_relative_path(path), "rb") as f:
            return f.read()

    def write_relative_path(self, path: str, data: bytes) -> Attachment:
        file_path = self._resolve_relative_path(path)
        with open(file_path, "wb") as file:
            file.write(data)
            filesize = file.tell()
        return Attachment(
            filename=file_path.name,
            filesize=filesize,
            url=str(file_path.relative_to(self.service.base_path)),
        )

    def _resolve_relative_path(self, path: str) -> Path:
        abs_path = (self.base_path / path).resolve()

        if not str(abs_path).startswith(str(self.base_path)):
            print("Error")
            raise ValueError(f"Directory traversal is not allowed! - {abs_path}")

        if abs_path.is_dir() or str(path).endswith("/"):
            target_path = abs_path
            try:
                target_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(e)
        elif abs_path.is_file():
            target_path = abs_path.parent
            try:
                target_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(e)
        else:
            if str(path).split(".")[-1] in ["txt", "pdf", "docx", "jpg", "png"]:
                target_path = abs_path.parent
                target_path.mkdir(parents=True, exist_ok=True)
                abs_path.touch()
            else:
                target_path = abs_path
                target_path.mkdir(parents=True, exist_ok=True)

        return abs_path

    def list_relative_path(self, path: str) -> List[str]:
        path = self.base_path / path
        base = self._resolve_relative_path(path)
        if not base.exists() or not base.is_dir():
            return []
        return [str(p.relative_to(self.base_path)) for p in base.iterdir()]

    def list_attachments(self, path: str) -> List[Attachment]:
        base_path = self.service.base_path / path
        base = self._resolve_relative_path(base_path)
        attachments = []

        if not base.exists() or not base.is_dir():
            return attachments

        for file in base.iterdir():
            if file.is_file():
                attachments.append(
                    Attachment(
                        filename=file.name,
                        filesize=file.stat().st_size,
                        url=str(file.relative_to(self.service.base_path / path)),
                    )
                )
        return attachments
