#!/usr/bin/env nix-shell
#!nix-shell -p python3 -p nix-prefetch-git -p nix -i python3

import json
import shutil
import re
import sys
import os
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any, Tuple
import xml.etree.ElementTree as ET
import urllib.request
import urllib.error
import subprocess
import tempfile
#from dataclasses import dataclass, field, InitVar
from enum import Enum, auto
from urllib.parse import urlparse, urljoin, ParseResult
import logging

ROOT = Path(__file__).parent.parent.resolve();
LOCK_PATH = ROOT.joinpath("repos.json.lock")
MANIFEST_PATH = ROOT.joinpath("repos.json")
EVALREPO_PATH = ROOT.joinpath("lib/evalRepo.nix")

Url = ParseResult

logger = logging.getLogger(__name__)


class NurError(Exception):
    pass


def fetch_commit_from_feed(url: str) -> str:
    req = urllib.request.urlopen(url)
    try:
        xml = req.read()
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
        ["nix-prefetch-url", "--name", "source", "--unpack", "--print-path", url])
    sha256, path = data.decode().strip().split("\n")
    return sha256, Path(path)


#@dataclass
class GithubRepo():
    def __init__(self, owner: str, name: str) -> None:
        self.owner = owner
        self.name = name

    #owner: str
    #name: str

    def url(self, path: str) -> str:
        return urljoin(f"https://github.com/{self.owner}/{self.name}/", path)

    def latest_commit(self) -> str:
        return fetch_commit_from_feed(self.url("commits/master.atom"))

    def prefetch(self, ref: str) -> Tuple[str, Path]:
        return nix_prefetch_zip(self.url(f"archive/{ref}.tar.gz"))


class GitlabRepo():
    def __init__(self, domain: str, owner: str, name: str) -> None:
        self.domain = domain
        self.owner = owner
        self.name = name

    def latest_commit(self) -> str:
        url = f"https://{self.domain}/{self.owner}/{self.name}/commits/master?format=atom"
        return fetch_commit_from_feed(url)

    def prefetch(self, ref: str) -> Tuple[str, Path]:
        url = f"https://{self.domain}/api/v4/projects/{self.owner}%2F{self.name}/repository/archive.tar.gz?sha={ref}"
        return nix_prefetch_zip(url)


class RepoType(Enum):
    GITHUB = auto()
    GITLAB = auto()
    GIT = auto()

    @staticmethod
    def from_spec(spec: 'RepoSpec') -> 'RepoType':
        if spec.url.hostname == "github.com" and not spec.submodules:
            return RepoType.GITHUB
        if (spec.url.hostname == "gitlab.com" or spec.type == "gitlab") \
                and not spec.submodules:
            return RepoType.GITLAB
        else:
            return RepoType.GIT


#@dataclass
class Repo():
    def __init__(self, spec: 'RepoSpec', rev: str, sha256: str) -> None:
        self.__post_init__(spec)
        self.rev = rev
        self.sha256 = sha256

    #spec: InitVar['RepoSpec']
    #rev: str
    #sha256: str

    #name: str = field(init=False)
    #url: Url = field(init=False)
    ##type: RepoType = field(init=False)
    #submodules: bool = field(init=False)

    def __post_init__(self, spec: 'RepoSpec'):
        self.name = spec.name
        self.url = spec.url
        self.submodules = spec.submodules
        self.type = RepoType.from_spec(spec)


#@dataclass
class RepoSpec():
    def __init__(self, name: str, url: Url, nix_file: str, submodules: bool,
                 type_: str) -> None:
        self.name = name
        self.url = url
        self.nix_file = nix_file
        self.submodules = submodules
        self.type = type_

    #name: str
    #url: Url
    #nix_file: str
    #submodules: bool


def prefetch_git(spec: RepoSpec) -> Tuple[str, str, Path]:
    url = spec.url.geturl()
    cmd = ["nix-prefetch-git"]
    if spec.submodules:
        cmd += ["--fetch-submodules"]
    cmd += [url]
    result = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise NurError(
            f"Failed to prefetch git repository {url}: {result.stderr}")

    metadata = json.loads(result.stdout)
    lines = result.stderr.decode("utf-8").split("\n")
    repo_path = re.search("path is (.+)", lines[-5])
    assert repo_path is not None
    path = Path(repo_path.group(1))
    return metadata["rev"], metadata["sha256"], path


def prefetch_github(spec: RepoSpec, locked_repo: Optional[Repo]
                    ) -> Tuple[str, str, Optional[Path]]:
    github_path = Path(spec.url.path)
    repo = GithubRepo(github_path.parts[1], github_path.parts[2])
    commit = repo.latest_commit()
    if locked_repo is not None:
        if locked_repo.rev == commit and \
                locked_repo.submodules == spec.submodules:
            return locked_repo.rev, locked_repo.sha256, None
    sha256, path = repo.prefetch(commit)
    return commit, sha256, path


def prefetch_gitlab(spec: RepoSpec, locked_repo: Optional[Repo]
                    ) -> Tuple[str, str, Optional[Path]]:
    gitlab_path = Path(spec.url.path)
    repo = GitlabRepo(spec.url.hostname, gitlab_path.parts[-2],
                      gitlab_path.parts[-1])
    commit = repo.latest_commit()
    if locked_repo is not None:
        if locked_repo.rev == commit and \
                locked_repo.submodules == spec.submodules:
            return locked_repo.rev, locked_repo.sha256, None
    sha256, path = repo.prefetch(commit)
    return commit, sha256, path


def prefetch(spec: RepoSpec,
             locked_repo: Optional[Repo]) -> Tuple[Repo, Optional[Path]]:

    repo_type = RepoType.from_spec(spec)
    if repo_type == RepoType.GITHUB:
        commit, sha256, path = prefetch_github(spec, locked_repo)
    elif repo_type == RepoType.GITLAB:
        commit, sha256, path = prefetch_gitlab(spec, locked_repo)
    else:
        commit, sha256, path = prefetch_git(spec)

    return Repo(spec, commit, sha256), path


def nixpkgs_path() -> str:
    cmd = ["nix-instantiate", "--find-file", "nixpkgs"]
    path = subprocess.check_output(cmd).decode("utf-8").strip()
    return str(Path(path).resolve())


def eval_repo(spec: RepoSpec, repo_path: Path) -> None:
    with tempfile.TemporaryDirectory() as d:
        eval_path = Path(d).joinpath("default.nix")
        with open(eval_path, "w") as f:
            f.write(f"""
                    with import <nixpkgs> {{}};
import {EVALREPO_PATH} {{
  name = "{spec.name}";
  url = "{spec.url}";
  src = {repo_path.joinpath(spec.nix_file)};
  inherit pkgs lib;
}}
""")

        cmd = [
            "nix-env",
            "-f", str(eval_path),
            "-qa", "*",
            "--meta",
            "--xml",
            "--option", "restrict-eval", "true",
            "--drv-path",
            "--show-trace",
            "-I", f"nixpkgs={nixpkgs_path()}",
            "-I", str(repo_path),
            "-I", str(eval_path),
            "-I", str(EVALREPO_PATH),
        ] # yapf: disable

        print(f"$ {' '.join(cmd)}")
        proc = subprocess.Popen(
            cmd, env=dict(PATH=os.environ["PATH"]), stdout=subprocess.PIPE)
        res = proc.wait()
        if res != 0:
            raise NurError(
                f"{spec.name} does not evaluate:\n$ {' '.join(cmd)}")


def update(spec: RepoSpec, locked_repo: Optional[Repo]) -> Repo:
    repo, repo_path = prefetch(spec, locked_repo)

    if repo_path:
        eval_repo(spec, repo_path)
    return repo


def update_lock_file(repos: List[Repo]):
    locked_repos = {}
    for repo in repos:
        locked_repo: Dict[str, Any] = dict(
            rev=repo.rev, sha256=repo.sha256, url=repo.url.geturl())
        if repo.submodules:
            locked_repo["submodules"] = True
        locked_repos[repo.name] = locked_repo

    tmp_file = str(LOCK_PATH) + "-new"
    with open(tmp_file, "w") as lock_file:
        json.dump(
            dict(repos=locked_repos), lock_file, indent=4, sort_keys=True)

    shutil.move(tmp_file, LOCK_PATH)


def main() -> None:
    if LOCK_PATH.exists():
        with open(LOCK_PATH) as f:
            lock_manifest = json.load(f)
    else:
        lock_manifest = dict(repos={})

    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    repos = []

    for name, repo in manifest["repos"].items():
        url = urlparse(repo["url"])
        repo_json = lock_manifest["repos"].get(name, None)
        spec = RepoSpec(name, url, repo.get("file", "default.nix"),
                        repo.get("submodules", False), repo.get("type", None))
        if repo_json and repo_json["url"] != url.geturl():
            repo_json = None
        locked_repo = None
        if repo_json is not None:
            locked_repo = Repo(spec, repo_json["rev"], repo_json["sha256"])

        try:
            repos.append(update(spec, locked_repo))
        except Exception as e:
            if locked_repo is None:
                # likely a repository added in a pull request, make it fatal then
                raise
            logger.exception(f"Failed to updated repo: {spec.name}")
            repos.append(locked_repo)

    update_lock_file(repos)


if __name__ == "__main__":
    main()
