import json
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Union
from urllib.parse import ParseResult, urlparse

Url = ParseResult


class LockedVersion:
    def __init__(
        self, url: Url, rev: str, sha256: str, submodules: bool = False
    ) -> None:
        self.url = url
        self.rev = rev
        self.sha256 = sha256
        self.submodules = submodules

    def as_json(self) -> Dict[str, Union[bool, str]]:
        d = dict(
            url=self.url.geturl(),
            rev=self.rev,
            sha256=self.sha256,
        )
        if self.submodules:
            d["submodules"] = self.submodules
        return d


class RepoType(Enum):
    GITHUB = auto()
    GITLAB = auto()
    GIT = auto()

    @staticmethod
    def from_repo(repo: "Repo", type_: str) -> "RepoType":
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
        type_: str,
        file_: Optional[str],
        locked_version: Optional[LockedVersion],
    ) -> None:
        self.name = name
        self.url = url
        self.submodules = submodules
        if file_ is None:
            self.file = "default.nix"
        else:
            self.file = file_
        self.locked_version = None

        if (
            locked_version is not None
            and locked_version.url != url.geturl()
            and locked_version.submodules == submodules
        ):
            self.locked_version = locked_version

        self.type = RepoType.from_repo(self, type_)


class Manifest:
    def __init__(self, repos: List[Repo]) -> None:
        self.repos = repos


def _load_locked_versions(path: Path) -> Dict[str, LockedVersion]:
    with open(path) as f:
        data = json.load(f)

    locked_versions = {}

    for name, repo in data["repos"].items():
        url = urlparse(repo["url"])
        rev = repo["rev"]
        sha256 = repo["sha256"]
        locked_versions[name] = LockedVersion(url, rev, sha256)

    return locked_versions


def load_locked_versions(path: Path) -> Dict[str, LockedVersion]:
    if path.exists():
        return _load_locked_versions(path)
    else:
        return {}


def load_manifest(manifest_path: Union[str, Path], lock_path) -> Manifest:
    locked_versions = load_locked_versions(lock_path)

    with open(manifest_path) as f:
        data = json.load(f)

    repos = []
    for name, repo in data["repos"].items():
        url = urlparse(repo["url"])
        submodules = repo.get("submodules", False)
        file_ = repo.get("file", "default.nix")
        type_ = repo.get("type", None)
        locked_version = locked_versions.get(name)
        repos.append(Repo(name, url, submodules, type_, file_, locked_version))

    return Manifest(repos)
