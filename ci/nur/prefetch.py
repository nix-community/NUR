import json
import re
import subprocess
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from .error import NurError
from .manifest import LockedVersion, Repo, RepoType


def fetch_commit_from_feed(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "nur-updater"})
    res = urllib.request.urlopen(req)
    try:
        xml = res.read()
        root = ET.fromstring(xml)
        ns = "{http://www.w3.org/2005/Atom}"
        xpath = f"./{ns}entry/{ns}link"
        commit_link = root.find(xpath)
        if commit_link is None:
            raise NurError(f"No commits found in repository feed {url}")
        return Path(urlparse(commit_link.attrib["href"]).path).parts[-1]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise NurError(f"Repository feed {url} not found")
        raise


def nix_prefetch_zip(url: str) -> Tuple[str, Path]:
    data = subprocess.check_output(
        ["nix-prefetch-url", "--name", "source", "--unpack", "--print-path", url]
    )
    sha256, path = data.decode().strip().split("\n")
    return sha256, Path(path)


class GithubRepo:
    def __init__(self, owner: str, name: str, branch: str) -> None:
        self.owner = owner
        self.name = name
        self.branch = branch

    def url(self, path: str) -> str:
        return urljoin(f"https://github.com/{self.owner}/{self.name}/", path)

    def latest_commit(self) -> str:
        return fetch_commit_from_feed(self.url(f"commits/{self.branch}.atom"))

    def prefetch(self, ref: str) -> Tuple[str, Path]:
        return nix_prefetch_zip(self.url(f"archive/{ref}.tar.gz"))


class GitlabRepo:
    def __init__(self, domain: str, path: List[str], branch: str) -> None:
        self.domain = domain
        self.path = path
        self.branch = branch

    def latest_commit(self) -> str:
        path = "/".join(self.path)
        url = f"https://{self.domain}/{path}/commits/{self.branch}?format=atom"
        return fetch_commit_from_feed(url)

    def prefetch(self, ref: str) -> Tuple[str, Path]:
        escaped_path = "%2F".join(self.path)
        url = f"https://{self.domain}/api/v4/projects/{escaped_path}/repository/archive.tar.gz?sha={ref}"
        return nix_prefetch_zip(url)


def prefetch_git(repo: Repo) -> Tuple[LockedVersion, Path]:
    cmd = ["nix-prefetch-git"]
    if repo.submodules:
        cmd += ["--fetch-submodules"]
    cmd += ["--rev", f"refs/heads/{repo.branch}"]
    cmd += [repo.url.geturl()]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdout, stderr = proc.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
        raise NurError(
            f"Timeout expired while prefetching git repository {repo.url.geturl()}"
        )

    if proc.returncode != 0:
        raise NurError(
            f"Failed to prefetch git repository {repo.url.geturl()}: {stderr.decode('utf-8')}"
        )

    metadata = json.loads(stdout)
    lines = stderr.decode("utf-8").split("\n")
    repo_path = re.search("path is (.+)", lines[-5])
    assert repo_path is not None
    path = Path(repo_path.group(1))
    rev = metadata["rev"]
    sha256 = metadata["sha256"]
    return LockedVersion(repo.url, rev, sha256, repo.submodules), path


def prefetch_github(repo: Repo) -> Tuple[LockedVersion, Optional[Path]]:
    github_path = Path(repo.url.path)
    gh_repo = GithubRepo(github_path.parts[1], github_path.parts[2], repo.branch)
    commit = gh_repo.latest_commit()
    locked_version = repo.locked_version
    if locked_version is not None:
        if locked_version.rev == commit:
            return locked_version, None
    sha256, path = gh_repo.prefetch(commit)

    return LockedVersion(repo.url, commit, sha256), path


def prefetch_gitlab(repo: Repo) -> Tuple[LockedVersion, Optional[Path]]:
    gitlab_path = Path(repo.url.path)
    hostname = repo.url.hostname
    assert hostname is not None, f"Expect a hostname for Gitlab repo: {repo.name}"
    gl_repo = GitlabRepo(hostname, list(gitlab_path.parts[1:]), repo.branch)
    commit = gl_repo.latest_commit()
    locked_version = repo.locked_version
    if locked_version is not None:
        if locked_version.rev == commit:
            return locked_version, None

    sha256, path = gl_repo.prefetch(commit)
    return LockedVersion(repo.url, commit, sha256), path


def prefetch(repo: Repo) -> Tuple[Repo, LockedVersion, Optional[Path]]:
    if repo.type == RepoType.GITHUB:
        locked_version, path = prefetch_github(repo)
    elif repo.type == RepoType.GITLAB:
        locked_version, path = prefetch_gitlab(repo)
    else:
        locked_version, path = prefetch_git(repo)

    return repo, locked_version, path
