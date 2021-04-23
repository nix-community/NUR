import json
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import ParseResult, urlparse

from .fileutils import PathType, to_path, write_json_file

Url = ParseResult


class LockedVersion:
    def __init__(
        self, url: Url, rev: str, sha256: str, submodules: bool = False
    ) -> None:
        self.url = url
        self.rev = rev
        self.sha256 = sha256
        self.submodules = submodules

    def __eq__(self, other: Any) -> bool:
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return False

    def as_json(self) -> Dict[str, Any]:
        d = dict(
            url=self.url.geturl(), rev=self.rev, sha256=self.sha256
        )  # type: Dict[str, Any]
        if self.submodules:
            d["submodules"] = self.submodules
        return d


class RepoType(Enum):
    GITHUB = auto()
    GITLAB = auto()
    GIT = auto()

    @staticmethod
    def from_repo(repo: "Repo", type_: Optional[str]) -> "RepoType":
        if repo.submodules:
            return RepoType.GIT
        if repo.url.hostname == "github.com":
            return RepoType.GITHUB
        if repo.url.hostname == "gitlab.com" or type_ == "gitlab":
            return RepoType.GITLAB
        else:
            return RepoType.GIT


class Repo:
    def __init__(
        self,
        name: str,
        url: Url,
        submodules: bool,
        supplied_type: Optional[str],
        file_: Optional[str],
        branch: Optional[str],
        locked_version: Optional[LockedVersion],
    ) -> None:
        self.name = name
        self.url = url
        self.submodules = submodules
        if file_ is None:
            self.file = "default.nix"
        else:
            self.file = file_
        if branch is None:
            self.branch = "master"
        else:
            self.branch = branch
        self.locked_version = None

        if (
            locked_version is not None
            and locked_version.url != url.geturl()
            and locked_version.submodules == submodules
        ):
            self.locked_version = locked_version

        self.supplied_type = supplied_type
        self.computed_type = RepoType.from_repo(self, supplied_type)

    @property
    def type(self) -> RepoType:
        return self.computed_type

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.name}>"

    def as_json(self) -> Dict[str, Any]:
        d = dict(url=self.url.geturl())  # type: Dict[str, Any]

        if self.submodules:
            d["submodules"] = self.submodules

        if self.supplied_type is not None:
            d["type"] = self.supplied_type

        if self.file is not None and self.file != "default.nix":
            d["file"] = self.file

        return d


class Manifest:
    def __init__(self, repos: List[Repo]) -> None:
        self.repos = repos

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {repr(self.repos)}>"


def _load_locked_versions(path: PathType) -> Dict[str, LockedVersion]:
    with open(path) as f:
        data = json.load(f)

    locked_versions = {}

    for name, repo in data["repos"].items():
        url = urlparse(repo["url"])
        rev = repo["rev"]
        sha256 = repo["sha256"]
        submodules = repo.get("submodules", False)
        locked_versions[name] = LockedVersion(url, rev, sha256, submodules)

    return locked_versions


def load_locked_versions(path: Path) -> Dict[str, LockedVersion]:
    if path.exists():
        return _load_locked_versions(path)
    else:
        return {}


def update_lock_file(repos: List[Repo], path: Path) -> None:
    locked_repos = {}
    for repo in repos:
        if repo.locked_version:
            locked_repos[repo.name] = repo.locked_version.as_json()

    write_json_file(dict(repos=locked_repos), path)


def load_manifest(manifest_path: PathType, lock_path: PathType) -> Manifest:
    locked_versions = load_locked_versions(to_path(lock_path))

    with open(manifest_path) as f:
        data = json.load(f)

    repos = []
    for name, repo in data["repos"].items():
        url = urlparse(repo["url"])
        submodules = repo.get("submodules", False)
        branch_ = repo.get("branch", "master")
        file_ = repo.get("file", "default.nix")
        type_ = repo.get("type", None)
        locked_version = locked_versions.get(name)
        repos.append(Repo(name, url, submodules, type_, file_, branch_, locked_version))

    return Manifest(repos)
