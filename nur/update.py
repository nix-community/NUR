#!/usr/bin/env nix-shell
#!nix-shell -p python37 -p nix-prefetch-git -p nix -i python3.7

import json
import shutil
import re
import sys
import os
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import xml.etree.ElementTree as ET
import urllib.request
import urllib.error
import subprocess
import tempfile
from dataclasses import dataclass, field, InitVar
from enum import Enum, auto
from urllib.parse import urlparse, urljoin, ParseResult

ROOT = Path(__file__).parent.parent
LOCK_PATH = ROOT.joinpath("repos.json.lock")
MANIFEST_PATH = ROOT.joinpath("repos.json")

Url = ParseResult


class NurError(Exception):
    pass


@dataclass
class GithubRepo():
    owner: str
    name: str

    def url(self, path: str) -> str:
        return urljoin(f"https://github.com/{self.owner}/{self.name}/", path)

    def latest_commit(self) -> str:
        req = urllib.request.urlopen(self.url("commits/master.atom"))
        try:
            xml = req.read()
            root = ET.fromstring(xml)
            ns = "{http://www.w3.org/2005/Atom}"
            xpath = f"./{ns}entry/{ns}link"
            commit_link = root.find(xpath)
            if commit_link is None:
                raise NurError(
                    f"No commits found in github repository {self.owner}/{self.name}"
                )
            return Path(urlparse(commit_link.attrib["href"]).path).parts[-1]
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise NurError(
                    f"Repository {self.owner}/{self.name} not found")
            raise

    def prefetch(self, ref: str) -> Tuple[str, Path]:
        data = subprocess.check_output([
            "nix-prefetch-url", "--unpack", "--print-path",
            self.url(f"archive/{ref}.tar.gz")
        ])
        sha256, path = data.decode().strip().split("\n")
        return sha256, Path(path)


class RepoType(Enum):
    GITHUB = auto()
    GIT = auto()

    @staticmethod
    def from_spec(spec: 'RepoSpec') -> 'RepoType':
        if spec.url.hostname == "github.com" and not spec.submodules:
            return RepoType.GITHUB
        else:
            return RepoType.GIT


@dataclass
class Repo():
    spec: InitVar['RepoSpec']
    rev: str
    sha256: str

    name: str = field(init=False)
    url: Url = field(init=False)
    type: RepoType = field(init=False)
    submodules: bool = field(init=False)

    def __post_init__(self, spec: 'RepoSpec'):
        self.name = spec.name
        self.url = spec.url
        self.submodules = spec.submodules
        self.type = RepoType.from_spec(spec)


@dataclass
class RepoSpec():
    name: str
    url: Url
    nix_file: str
    submodules: bool


def prefetch_git(spec: RepoSpec) -> Tuple[str, str, Path]:
    url = spec.url.geturl()
    cmd = ["nix-prefetch-git"]
    if spec.submodules:
        cmd += ["--fetch-submodules"]
    cmd += [url]
    result = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise NurError(f"Failed to prefetch git repository {url}: {result.stderr}")

    metadata = json.loads(result.stdout)
    lines = result.stderr.decode("utf-8").split("\n")
    repo_path = re.search("path is (.+)", lines[-5])
    assert repo_path is not None
    path = Path(repo_path.group(1))
    return metadata["rev"], metadata["sha256"], path


def prefetch(spec: RepoSpec,
             locked_repo: Optional[Repo]) -> Tuple[Repo, Optional[Path]]:

    repo_type = RepoType.from_spec(spec)
    if repo_type == RepoType.GITHUB:
        github_path = Path(spec.url.path)
        gh_repo = GithubRepo(github_path.parts[1], github_path.parts[2])
        commit = gh_repo.latest_commit()
        if locked_repo is not None:
            if locked_repo.rev == commit and \
                    locked_repo.submodules == spec.submodules:
                return locked_repo, None
        sha256, path = gh_repo.prefetch(commit)
    else:
        commit, sha256, path = prefetch_git(spec)

    return Repo(spec, commit, sha256), path


def nixpkgs_path() -> str:
    cmd = ["nix", "eval", "(<nixpkgs>)"]
    return subprocess.check_output(cmd).decode("utf-8").strip()


def eval_repo(spec: RepoSpec, repo_path: Path) -> None:
    with tempfile.TemporaryDirectory() as d:
        eval_path = Path(d).joinpath("default.nix")
        with open(eval_path, "w") as f:
            f.write(f"""
                    with import <nixpkgs> {{}};
callPackages {repo_path.joinpath(spec.nix_file)} {{}}
""")
        nix_path = [
            f"nixpkgs={nixpkgs_path()}",
            str(repo_path),
            str(eval_path),
        ]

        env = dict(
            NIX_PATH=":".join(nix_path),
            PATH=os.environ["PATH"],
        )

        cmd = [
            "nix-env", "-f",
            str(eval_path), "-qa", "*", "--meta", "--xml", "--option",
            "restrict-eval", "true", "--drv-path", "--show-trace"
        ]
        proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE)
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
                        repo.get("submodules", False))
        if repo_json and repo_json["url"] != url.geturl():
            repo_json = None
        locked_repo = None
        if repo_json is not None:
            locked_repo = Repo(spec, repo_json["rev"], repo_json["sha256"])

        try:
            repos.append(update(spec, locked_repo))
        except NurError as e:
            print(f"failed to update repository {name}: {e}", file=sys.stderr)
            if locked_repo:
                repos.append(locked_repo)

    update_lock_file(repos)


if __name__ == "__main__":
    main()
