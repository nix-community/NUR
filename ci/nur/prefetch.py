import json
import os
import re
import subprocess
import asyncio
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse, ParseResult

from .error import NurError
from .manifest import LockedVersion, Repo, RepoType

Url = ParseResult

async def nix_prefetch_zip(url: str) -> Tuple[str, Path]:
    proc = await asyncio.create_subprocess_exec(
        *["nix-prefetch-url", "--name", "source", "--unpack", "--print-path", url],
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(stderr.decode())

    sha256, path = stdout.decode().strip().split("\n")
    return sha256, Path(path)


class GitPrefetcher:
    def __init__(self, repo: Repo) -> None:
        self.repo = repo

    async def latest_commit(self) -> str:
        proc = await asyncio.create_subprocess_exec(
            *["git", "ls-remote", self.repo.url.geturl(), self.repo.branch or "HEAD"],
            env={**os.environ, "GIT_ASKPASS": "", "GIT_TERMINAL_PROMPT": "0"},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(stderr.decode())

        return stdout.decode().split(maxsplit=1)[0]

    async def prefetch(self, ref: str) -> Tuple[str, Path]:
        cmd = ["nix-prefetch-git"]
        if self.repo.submodules:
            cmd += ["--fetch-submodules"]
        if self.repo.branch:
            cmd += ["--rev", f"refs/heads/{self.repo.branch}"]
        cmd += [self.repo.url.geturl()]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
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
    async def prefetch(self, ref: str) -> Tuple[str, Path]:
        return await nix_prefetch_zip(f"{self.repo.url.geturl()}/archive/{ref}.tar.gz")


class GitlabPrefetcher(GitPrefetcher):
    async def prefetch(self, ref: str) -> Tuple[str, Path]:
        hostname = self.repo.url.hostname
        assert (
            hostname is not None
        ), f"Expect a hostname for Gitlab repo: {self.repo.name}"
        path = Path(self.repo.url.path)
        escaped_path = "%2F".join(path.parts[1:])
        url = f"https://{hostname}/api/v4/projects/{escaped_path}/repository/archive.tar.gz?sha={ref}"
        return await nix_prefetch_zip(url)


async def prefetch(repo: Repo) -> Tuple[Repo, LockedVersion, Optional[Path]]:
    prefetcher: GitPrefetcher
    if repo.type == RepoType.GITHUB:
        prefetcher = GithubPrefetcher(repo)
    elif repo.type == RepoType.GITLAB:
        prefetcher = GitlabPrefetcher(repo)
    else:
        prefetcher = GitPrefetcher(repo)

    commit = await prefetcher.latest_commit()
    locked_version = repo.locked_version
    if locked_version is not None:
        if locked_version.rev == commit:
            return repo, locked_version, None

    sha256, path = await prefetcher.prefetch(commit)
    return repo, LockedVersion(repo.url, commit, sha256, repo.submodules), path
