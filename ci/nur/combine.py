import logging
import os
import shutil
import subprocess
from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, List, Optional

from .fileutils import chdir, write_json_file
from .manifest import Repo, load_manifest, update_lock_file
from .path import LOCK_PATH, MANIFEST_PATH, ROOT

logger = logging.getLogger(__name__)


def load_combined_repos(path: Path) -> Dict[str, Repo]:
    combined_manifest = load_manifest(
        path.joinpath("repos.json"), path.joinpath("repos.json.lock")
    )
    repos = {}
    for repo in combined_manifest.repos:
        repos[repo.name] = repo
    return repos


def repo_source(name: str) -> str:
    cmd = ["nix-build", str(ROOT), "--no-out-link", "-A", f"repo-sources.{name}"]
    out = subprocess.check_output(cmd)
    return out.strip().decode("utf-8")


def repo_changed() -> bool:
    diff_cmd = subprocess.Popen(["git", "diff", "--staged", "--exit-code"])
    return diff_cmd.wait() == 1


def commit_files(files: List[str], message: str) -> None:
    cmd = ["git", "add"]
    cmd.extend(files)
    subprocess.check_call(cmd)
    if repo_changed():
        subprocess.check_call(["git", "commit", "-m", message])


def commit_repo(repo: Repo, message: str, path: Path) -> Repo:
    repo_path = path.joinpath(repo.name).resolve()

    tmp: Optional[TemporaryDirectory] = TemporaryDirectory(prefix=str(repo_path.parent))
    assert tmp is not None

    try:
        shutil.copytree(repo_source(repo.name), tmp.name, symlinks=True)
        shutil.rmtree(repo_path, ignore_errors=True)
        os.rename(tmp.name, repo_path)
        tmp = None
    finally:
        if tmp is not None:
            tmp.cleanup()

    with chdir(str(path)):
        commit_files([str(repo_path)], message)

    return repo


def repo_link(path: Path) -> str:
    commit = subprocess.check_output(["git", "-C", path, "rev-parse", "HEAD"])
    rev = commit.decode("utf-8").strip()[:10]
    return f"https://github.com/nix-community/nur-combined/commit/{rev}"


def update_combined_repo(
    combined_repo: Optional[Repo], repo: Repo, path: Path
) -> Optional[Repo]:
    if repo.locked_version is None:
        return None

    new_rev = repo.locked_version.rev
    if combined_repo is None:
        message = f"{repo.name}: init at {new_rev[:10]} ({repo_link(path)})"
        repo = commit_repo(repo, message, path)
        return repo

    assert combined_repo.locked_version is not None
    old_rev = combined_repo.locked_version.rev

    if combined_repo.locked_version == repo.locked_version:
        return repo

    if new_rev != old_rev:
        message = f"{repo.name}: {old_rev[:10]} -> {new_rev[:10]}"
    else:
        message = f"{repo.name}: update"

    repo = commit_repo(repo, message, path)
    return repo


def remove_repo(repo: Repo, path: Path) -> None:
    repo_path = path.joinpath("repos", repo.name).resolve()
    if repo_path.exists():
        shutil.rmtree(repo_path)
    with chdir(path):
        commit_files([str(repo_path)], f"{repo.name}: remove")


def update_manifest(repos: List[Repo], path: Path) -> None:
    d = {}

    for repo in repos:
        d[repo.name] = repo.as_json()
    write_json_file(dict(repos=d), path)


def update_combined(path: Path) -> None:
    manifest = load_manifest(MANIFEST_PATH, LOCK_PATH)

    combined_repos = load_combined_repos(path)

    repos_path = path.joinpath("repos")
    os.makedirs(repos_path, exist_ok=True)

    updated_repos = []

    for repo in manifest.repos:
        combined_repo = None
        if repo.name in combined_repos:
            combined_repo = combined_repos[repo.name]
            del combined_repos[repo.name]
        try:
            new_repo = update_combined_repo(combined_repo, repo, repos_path)
        except Exception:
            logger.exception(f"Failed to updated repository {repo.name}")
            continue

        if new_repo is not None:
            updated_repos.append(new_repo)

    for combined_repo in combined_repos.values():
        remove_repo(combined_repo, path)

    update_manifest(updated_repos, path.joinpath("repos.json"))

    update_lock_file(updated_repos, path.joinpath("repos.json.lock"))

    with chdir(path):
        commit_files(["repos.json", "repos.json.lock"], "update repos.json + lock")


def setup_combined() -> None:
    manifest_path = "repos.json"

    if not Path(".git").exists():
        cmd = ["git", "init", "."]
        subprocess.check_call(cmd)

    if not os.path.exists(manifest_path):
        write_json_file(dict(repos={}), manifest_path)

    manifest_lib = "lib"
    shutil.copytree(str(ROOT.joinpath("lib")), manifest_lib, symlinks=True)
    default_nix = "default.nix"
    shutil.copy(ROOT.joinpath("default.nix"), default_nix)

    vcs_files = [manifest_path, manifest_lib, default_nix]

    commit_files(vcs_files, "update code")


def combine_command(args: Namespace) -> None:
    combined_path = Path(args.directory)

    with chdir(combined_path):
        setup_combined()
    update_combined(combined_path)
