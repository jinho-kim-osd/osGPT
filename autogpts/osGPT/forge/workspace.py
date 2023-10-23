from __future__ import annotations
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from pydantic import BaseModel, Field

from forge.sdk import Workspace as WorkspaceService
from .schema import Project


class FileInfo(BaseModel):
    """
    A Pydantic model representing information about a file.
    """

    absolute_url: str
    relative_url: Optional[str] = None
    filename: str
    filesize: int
    updated_at: datetime


class Workspace(BaseModel):
    name: str
    projects: List[Project] = Field(default_factory=list)
    project_key_to_path: Dict[str, Path] = Field(default_factory=dict)
    service: WorkspaceService

    class Config:
        arbitrary_types_allowed = True

    def reset(self):
        """
        Reset the workspace by clearing all projects and project key-path mappings.
        """
        self.projects = []
        self.project_key_to_path = {}

    def add_project(self, project: Project):
        """
        Add a project to the workspace.
        """
        self.projects.append(project)

    def get_project(self, project_key: str) -> Project:
        """
        Retrieve a project by its key.

        Args:
            project_key (str): The key of the desired project.

        Returns:
            Project: The project associated with the given key.

        Raises:
            ValueError: If no project is found with the given key.
        """
        for project in self.projects:
            if project.key == project_key:
                return project
        raise ValueError(f"Project with key {project_key} not found")

    def register_project_key_path(self, key: str, relative_path: str):
        """
        Register a key to a specific project path.

        Args:
            key (str): The key to be registered.
            relative_path (str): The relative path associated with the key.
        """
        absolute_path = self.base_path / relative_path
        absolute_path.mkdir(parents=True, exist_ok=True)
        self.project_key_to_path[key] = absolute_path

    def get_project_path_by_key(self, key: str) -> Path:
        """
        Retrieve the project path associated with a given key.

        Args:
            key (str): The key whose associated path is to be retrieved.

        Returns:
            Path: The path associated with the given key, if found.

        Raises:
            ValueError: If no path is registered for the given key.
        """
        return self.project_key_to_path.get(key)

    def read_by_key(self, key: str, path: str) -> bytes:
        """
        Read data from a specific project path using its registered key.

        Args:
            key (str): The key associated with the project path.
            path (str): The specific path within the project from where to read data.

        Returns:
            bytes: The data read from the specified path.

        Raises:
            ValueError: If no registered path for the given key or an error occurs while reading the file.
        """
        project_root = self.get_project_path_by_key(key)
        if not project_root:
            raise ValueError(f"No registered path for key {key}!")
        full_path = project_root / path
        with open(full_path, "rb") as file:
            return file.read()

    def list_files_by_key(self, key: str, path: Optional[str] = None) -> List[FileInfo]:
        """
        List all files and directories in a specified project path using its registered key.

        Args:
            key (str): The key associated with the project path.
            path (str, optional): The specific path within the project to list files and directories. Defaults to None.

        Returns:
            List[FileInfo]: A list of FileInfo instances, each containing information about a file or directory.

        Raises:
            ValueError: If no registered path for the given key or the specified path does not exist.
        """
        project_root = self.get_project_path_by_key(key)
        if not project_root:
            raise ValueError(f"No registered path for key {key}!")

        target_path = project_root if path is None else project_root / path
        if not target_path.exists():
            raise ValueError(f"Path {target_path} does not exist!")

        files_info = []
        for item in target_path.iterdir():
            relative_path = self.get_relative_path_by_key(key, item)
            updated_at = datetime.fromtimestamp(item.stat().st_mtime)
            file_info = FileInfo(
                absolute_url=str(item),
                relative_url=relative_path,
                filename=item.name,
                filesize=item.stat().st_size,
                updated_at=updated_at,
            )
            files_info.append(file_info)

        return files_info

    def get_relative_path_by_key(self, key: str, absolute_path: Path) -> str:
        """
        Retrieve the relative path of a file within the project directory identified by the key.

        Args:
            key (str): The key associated with the project directory.
            absolute_path (Path): The absolute path of the file.

        Returns:
            str: The relative path of the file within the project directory.

        Raises:
            ValueError: If no registered path for the given key.
        """
        project_root = self.get_project_path_by_key(key)
        if not project_root:
            raise ValueError(f"No registered path for key {key}!")
        return str(absolute_path.relative_to(project_root))

    def write_file_by_key(self, key: str, path: str, data: bytes) -> FileInfo:
        """
        Write data to a specific project path using its registered key and return the file info.

        Args:
            key (str): The key associated with the project path.
            path (str): The specific path within the project where to write data.
            data (bytes): The data to be written.

        Returns:
            FileInfo: An instance of FileInfo containing information about the written file.

        Raises:
            ValueError: If no registered path for the given key or an error occurs while writing to the file.
        """
        project_root = self.get_project_path_by_key(key)
        if not project_root:
            raise ValueError(f"No registered path for key {key}!")
        full_path = project_root / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "wb") as file:
            file.write(data)

        relative_path = self.get_relative_path_by_key(key, full_path)
        updated_at = datetime.fromtimestamp(full_path.stat().st_mtime)

        file_info = FileInfo(
            absolute_url=str(full_path),
            relative_url=relative_path,
            filename=full_path.name,
            filesize=full_path.stat().st_size,
            updated_at=updated_at,
        )
        return file_info

    @property
    def base_path(self) -> Path:
        return self.service.base_path

    def read(self, task_id: str, path: str):
        return self.service.read(task_id, path)

    def write(self, task_id: str, path: str, data: bytes):
        return self.service.write(task_id, path, data)
