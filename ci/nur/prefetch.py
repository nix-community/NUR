import json
import os
import re
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import ParseResult

from .error import NurError
from .manifest import LockedVersion, Repo, RepoType

Url = ParseResult


def nix_prefetch_zip(url: str) -> Tuple[str, Path]:
    data = subprocess.check_output(
        ["nix-prefetch-url", "--name", "source", "--unpack", "--print-path", url]
    )
    sha256, path = data.decode().strip().split("\n")
    return sha256, Path(path)


class GitPrefetcher:
    def __init__(self, repo: Repo) -> None:
        self.repo = repo

    def latest_commit(self) -> str:
        data = subprocess.check_output(
            ["git", "ls-remote", self.repo.url.geturl(), self.repo.branch or "HEAD"],
            env={**os.environ, "GIT_ASKPASS": "", "GIT_TERMINAL_PROMPT": "0"},
        )
        return data.decode().split(maxsplit=1)[0]

    def prefetch(self, ref: str) -> Tuple[str, Path]:
        cmd = ["nix-prefetch-git"]
        if self.repo.submodules:
            cmd += ["--fetch-submodules"]
        if self.repo.branch:
            cmd += ["--rev", f"refs/heads/{self.repo.branch}"]
        cmd += [self.repo.url.geturl()]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            stdout, stderr = proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            raise NurError(
                f"Timeout expired while prefetching git repository {self. repo.url.geturl()}"
            )

        if proc.returncode != 0:
            raise NurError(
                f"Failed to prefetch git repository {self.repo.url.geturl()}: {stderr.decode('utf-8')}"
            )

        metadata = json.loads(stdout)
        lines = stderr.decode("utf-8").split("\n")
        repo_path = re.search("path is (.+)", lines[-5])
        assert repo_path is not None
        path = Path(repo_path.group(1))
        sha256 = metadata["sha256"]
        return sha256, path


class GithubPrefetcher(GitPrefetcher):
    def prefetch(self, ref: str) -> Tuple[str, Path]:
        return nix_prefetch_zip(f"{self.repo.url.geturl()}/archive/{ref}.tar.gz")


class GitlabPrefetcher(GitPrefetcher):
    def prefetch(self, ref: str) -> Tuple[str, Path]:
        hostname = self.repo.url.hostname
        assert (
            hostname is not None
        ), f"Expect a hostname for Gitlab repo: {self.repo.name}"
        path = Path(self.repo.url.path)
        escaped_path = "%2F".join(path.parts[1:])
        url = f"https://{hostname}/api/v4/projects/{escaped_path}/repository/archive.tar.gz?sha={ref}"
        return nix_prefetch_zip(url)


def prefetch(repo: Repo) -> Tuple[Repo, LockedVersion, Optional[Path]]:
    prefetcher: GitPrefetcher
    if repo.type == RepoType.GITHUB:
        prefetcher = GithubPrefetcher(repo)
    elif repo.type == RepoType.GITLAB:
        prefetcher = GitlabPrefetcher(repo)
    else:
        prefetcher = GitPrefetcher(repo)

    commit = prefetcher.latest_commit()
    locked_version = repo.locked_version
    if locked_version is not None:
        if locked_version.rev == commit:
            return repo, locked_version, None

    sha256, path = prefetcher.prefetch(commit)
    return repo, LockedVersion(repo.url, commit, sha256, repo.submodules), path
