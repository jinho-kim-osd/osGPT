from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Optional

from pydantic import BaseModel, Field

from forge.sdk import Workspace as WorkspaceService
from .schema import Project


class Workspace(BaseModel):
    name: str
    projects: List[Project] = Field(default_factory=list)
    project_key_to_path: Dict[str, Path] = Field(default_factory=dict)
    service: WorkspaceService

    class Config:
        arbitrary_types_allowed = True

    def reset(self):
        self.projects = []
        self.project_key_to_path = {}

    def add_project(self, project: Project):
        self.projects.append(project)

    def get_project(self, project_key: str) -> Project:
        for project in self.projects:
            if project.key == project_key:
                return project
        raise ValueError(f"Project with key {project_key} not found")

    def register_project_key_path(self, key: str, relative_path: str):
        """Register a key to a specific project path."""
        absolute_path = self.base_path / relative_path
        absolute_path.mkdir(parents=True, exist_ok=True)
        self.project_key_to_path[key] = absolute_path

    def get_project_path_by_key(self, key: str) -> Path:
        """Get a project path by its registered key."""
        return self.project_key_to_path.get(key)

    def read_by_key(self, key: str, path: str) -> bytes:
        """Read data from a specific project path using its registered key."""
        project_root = self.get_project_path_by_key(key)
        if not project_root:
            raise ValueError(f"No registered path for key {key}!")
        full_path = project_root / path
        with open(full_path, "rb") as file:
            return file.read()

    def list_files_by_key(self, key: str, path: Optional[str] = None) -> List[Path]:
        """List all files and directories in the specified project path using its registered key."""
        project_root = self.get_project_path_by_key(key)
        if not project_root:
            raise ValueError(f"No registered path for key {key}!")

        target_path = project_root if path is None else project_root / path
        if not target_path.exists():
            raise ValueError(f"Path {target_path} does not exist!")

        return list(target_path.iterdir())

    def write_file_by_key(self, key: str, path: str, data: bytes) -> dict:
        """Write data to a specific project path using its registered key and return the file info."""
        project_root = self.get_project_path_by_key(key)
        if not project_root:
            raise ValueError(f"No registered path for key {key}!")
        full_path = project_root / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "wb") as file:
            file.write(data)

        file_info = {
            "url": str(full_path),
            "filename": full_path.name,
            "filesize": full_path.stat().st_size,  # get the file size
        }

        return file_info

    @property
    def base_path(self) -> Path:
        return self.service.base_path

    def read(self, task_id: str, path: str):
        return self.service.read(task_id, path)

    def write(self, task_id: str, path: str, data: bytes):
        return self.service.write(task_id, path, data)

    # def _resolve_relative_path(self, path: str) -> Path:
    #     abs_path = (self.base_path / path).resolve()

    #     if not str(abs_path).startswith(str(self.base_path)):
    #         print("Error")
    #         raise ValueError(f"Directory traversal is not allowed! - {abs_path}")

    #     if abs_path.is_dir() or str(path).endswith("/"):
    #         target_path = abs_path
    #         try:
    #             target_path.mkdir(parents=True, exist_ok=True)
    #         except Exception as e:
    #             print(e)
    #     elif abs_path.is_file():
    #         target_path = abs_path.parent
    #         try:
    #             target_path.mkdir(parents=True, exist_ok=True)
    #         except Exception as e:
    #             print(e)
    #     else:
    #         if str(path).split(".")[-1] in ["txt", "pdf", "docx", "jpg", "png"]:
    #             target_path = abs_path.parent
    #             target_path.mkdir(parents=True, exist_ok=True)
    #             # abs_path.touch()
    #         else:
    #             target_path = abs_path
    #             target_path.mkdir(parents=True, exist_ok=True)

    #     return abs_path

    # def list_relative_path(self, path: str) -> List[str]:
    #     path = self.base_path / path
    #     base = self._resolve_relative_path(path)
    #     if not base.exists() or not base.is_dir():
    #         return []
    #     return [str(p.relative_to(self.base_path)) for p in base.iterdir()]
