import json
import subprocess
import sys
from argparse import Namespace
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict


def index_repo(directory: Path, repo: str, expression_file: str) -> Dict[str, Any]:
    default_nix = directory.joinpath("default.nix")
    fetch_source_cmd = [
        "nix-build",
        "--builders",
        "",
        "--no-out-link",
        str(default_nix),
        "-A",
        f'repo-sources."{repo}"',
    ]

    repo_path = subprocess.check_output(fetch_source_cmd).strip().decode("utf-8")

    expression_path = Path(repo_path).joinpath(expression_file)

    with NamedTemporaryFile(mode="w") as f:
        expr = f"with import <nixpkgs> {{}}; callPackage {expression_path} {{}}"
        f.write(expr)
        f.flush()
        query_cmd = ["nix-env", "-qa", "*", "--json", "-f", str(f.name)]
        try:
            out = subprocess.check_output(query_cmd)
        except subprocess.CalledProcessError:
            print(f"failed to evaluate {repo}", file=sys.stderr)
            return {}

        raw_pkgs = json.loads(out)
        pkgs = {}
        for name, pkg in raw_pkgs.items():
            pkg["_attr"] = name
            pkg["_repo"] = repo
            position = pkg["meta"].get("position", None)
            # TODO commit hash
            prefix = f"https://github.com/nix-community/nur-combined/tree/master/repos/{repo}"
            if position is not None and position.startswith(repo_path):
                prefix_len = len(repo_path)
                stripped = position[prefix_len:]
                path, line = stripped.rsplit(":", 1)
                pkg["meta"]["position"] = f"{prefix}{path}#L{line}"
            else:
                pkg["meta"]["position"] = prefix
            pkgs[f"nur.repos.{repo}.{name}"] = pkg
        return pkgs


def index_command(args: Namespace) -> None:
    directory = Path(args.directory)
    manifest_path = directory.joinpath("repos.json")
    with open(manifest_path) as f:
        manifest = json.load(f)
    repos = manifest.get("repos", [])
    pkgs: Dict[str, Any] = {}

    for (repo, data) in repos.items():
        pkgs.update(index_repo(directory, repo, data.get("file", "default.nix")))

    json.dump(pkgs, sys.stdout, indent=4)
