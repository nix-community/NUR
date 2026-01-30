import json
import os
import re
import subprocess
import asyncio
import aiohttp
from pathlib import Path
from typing import Optional, Tuple, List
from urllib.parse import urlparse, ParseResult

from .error import NurError, RepositoryDeletedError
from .manifest import Repo, RepoType

Url = ParseResult

async def nix_prefetch_zip(url: str) -> Tuple[str, Path]:
    proc = await asyncio.create_subprocess_exec(
        *["nix-prefetch-url", "--name", "source", "--unpack", "--print-path", url],
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise NurError(
            f"Failed to prefetch git repository {url}: {stderr.decode()}"
        )

    sha256, path = stdout.decode().strip().split("\n")
    return sha256, Path(path)


def parse_pkt_lines(data: bytes) -> List[bytes]:
    i = 0
    lines = []
    while i < len(data):
        if i + 4 > len(data):
            break
        length = int(data[i:i+4], 16)
        i += 4
        if length == 0:
            continue
        line = data[i:i+length-4]
        i += length - 4
        lines.append(line)
    return lines


class GitPrefetcher:
    def __init__(self, repo: Repo) -> None:
        self.repo = repo

    async def latest_commit(self) -> str:
        info_url = f"{self.repo.url.geturl()}/info/refs?service=git-upload-pack"

        async with aiohttp.ClientSession() as session:
            async with session.get(info_url) as resp:
                if resp.status == 401:
                    raise RepositoryDeletedError(f"Repository deleted!")
                elif resp.status != 200:
                    raise NurError(f"Failed to get refs for {self.repo.url.geturl()}: {(await resp.read()).decode()}")
                raw = await resp.read()

        lines = parse_pkt_lines(raw)

        wanted = b"HEAD" if self.repo.branch is None else f"refs/heads/{self.repo.branch}".encode()

        for line in lines:
            # Strip capabilities after NUL
            if b"\x00" in line:
                line = line.split(b"\x00", 1)[0]

            parts = line.strip().split()
            if len(parts) == 2 and parts[1] == wanted:
                return parts[0].decode()

        raise NurError(f"Ref not found: {wanted.decode()}")

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
            stdout, stderr = await asyncio.wait_for(proc.communicate(), 30)
        except TimeoutError:
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
        if not repo_path:
            raise NurError(
                f"Failed to prefetch git repository {self.repo.url.geturl()}"
            )
        path = Path(repo_path.group(1))
        if not path:
            raise NurError(
                f"Failed to prefetch git repository {self.repo.url.geturl()}"
            )
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

def prefetcher_for(repo: Repo) -> GitPrefetcher:
    match repo.type:
        case RepoType.GITHUB:
            return GithubPrefetcher(repo)
        case RepoType.GITLAB:
            return GithubPrefetcher(repo)
        case _:
            return GitPrefetcher(repo)
