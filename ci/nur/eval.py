import logging
import os
import subprocess
import tempfile
from argparse import Namespace
from pathlib import Path
from urllib.parse import urlparse

from .error import EvalError
from .manifest import Repo
from .path import EVALREPO_PATH, nixpkgs_path

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

        canonicalized_eval_path = eval_path.resolve()
        # fmt: off
        cmd = [
            "nix-env",
            "-f", str(canonicalized_eval_path),
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
            "-I", str(canonicalized_eval_path),
            "-I", str(EVALREPO_PATH),
        ]
        # fmt: on

        logger.info(f"Evaluate repository {repo.name}")
        env = dict(PATH=os.environ["PATH"], NIXPKGS_ALLOW_UNSUPPORTED_SYSTEM="1")
        proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL)
        try:
            res = proc.wait(15)
        except subprocess.TimeoutExpired:
            raise EvalError(f"evaluation for {repo.name} timed out of after 15 seconds")
        if res != 0:
            raise EvalError(f"{repo.name} does not evaluate:\n$ {' '.join(cmd)}")


def eval_command(args: Namespace) -> None:
    logging.basicConfig(level=logging.INFO)

    repo_path = Path(args.directory)
    name = repo_path.name
    repo = Repo(
        name,
        urlparse("localhost"),
        False,
        None,
        None,
        None,
        None,
    )
    eval_repo(repo, repo_path)
    print("OK")
