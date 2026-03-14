import asyncio
import logging
import os
import tempfile
from argparse import Namespace
from pathlib import Path
from urllib.parse import urlparse

from .error import EvalError
from .manifest import Repo
from .path import EVALREPO_PATH, nixpkgs_path

logger = logging.getLogger(__name__)


async def eval_repo(repo: Repo, repo_path: Path) -> None:
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

        env = dict(PATH=os.environ["PATH"], NIXPKGS_ALLOW_UNSUPPORTED_SYSTEM="1")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), 180)
        except TimeoutError:
            proc.kill()
            raise EvalError(f"evaluation for {repo.name} timed out of after 3 minutes")
        if proc.returncode != 0:
            raise EvalError(
                f"{repo.name} does not evaluate:\n$ {' '.join(cmd)}\n\n{stderr.decode()}"
            )


async def eval_command(args: Namespace) -> None:
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
    await eval_repo(repo, repo_path)
    print("OK")
