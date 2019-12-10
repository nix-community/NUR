import logging
import os
import subprocess
import tempfile
from argparse import Namespace
from pathlib import Path

from .error import EvalError
from .manifest import Repo, load_manifest, update_lock_file
from .path import EVALREPO_PATH, LOCK_PATH, MANIFEST_PATH, nixpkgs_path
from .prefetch import prefetch

logger = logging.getLogger(__name__)


def eval_repo(repo: Repo, repo_path: Path) -> None:
    with tempfile.TemporaryDirectory() as d:
        eval_path = Path(d).joinpath("default.nix")
        with open(eval_path, "w") as f:
            f.write(
                f"""
                    with import <nixpkgs> {{}};
import {EVALREPO_PATH} {{
  name = "{repo.name}";
  url = "{repo.url}";
  src = {repo_path.joinpath(repo.file)};
  inherit pkgs lib;
}}
"""
            )

        # fmt: off
        cmd = [
            "nix-env",
            "-f", str(eval_path),
            "-qa", "*",
            "--meta",
            "--xml",
            "--allowed-uris", "https://static.rust-lang.org",
            "--option", "restrict-eval", "true",
            "--option", "allow-import-from-derivation", "true",
            "--drv-path",
            "--show-trace",
            "-I", f"nixpkgs={nixpkgs_path()}",
            "-I", str(repo_path),
            "-I", str(eval_path),
            "-I", str(EVALREPO_PATH),
        ]
        # fmt: on

        logger.info(f"Evaluate repository {repo.name}")
        proc = subprocess.Popen(
            cmd, env=dict(PATH=os.environ["PATH"]), stdout=subprocess.DEVNULL
        )
        try:
            res = proc.wait(5)
        except subprocess.TimeoutExpired:
            raise EvalError(f"evaluation for {repo.name} timed out of after 5 seconds")
        if res != 0:
            raise EvalError(f"{repo.name} does not evaluate:\n$ {' '.join(cmd)}")


def update(repo: Repo) -> Repo:
    repo, locked_version, repo_path = prefetch(repo)

    if repo_path:
        eval_repo(repo, repo_path)

    repo.locked_version = locked_version
    return repo


def update_command(args: Namespace) -> None:
    logging.basicConfig(level=logging.INFO)

    manifest = load_manifest(MANIFEST_PATH, LOCK_PATH)

    for repo in manifest.repos:
        try:
            update(repo)
        except EvalError as err:
            if repo.locked_version is None:
                # likely a repository added in a pull request, make it fatal then
                raise
            # Do not print stack traces
            logger.error(f"repository {repo.name} failed to evaluate: {err}")
        except Exception:
            # for non-evaluation errors we want the stack trace
            logger.exception(f"Failed to updated repository {repo.name}")

    update_lock_file(manifest.repos, LOCK_PATH)
