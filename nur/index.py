import json
import subprocess
from argparse import Namespace
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict

from .path import ROOT


def index_repo(repo: str, expression_file: str) -> Dict[str, Any]:
    fetch_source_cmd = [
        "nix-build",
        str(ROOT),
        "-A",
        f"repo-sources.{repo}",
        "--no-out-link",
    ]

    repo_path = subprocess.check_output(fetch_source_cmd).strip()

    expression_path = Path(repo_path.decode("utf-8")).joinpath(expression_file)

    with NamedTemporaryFile(mode="w") as f:
        expr = f"with import <nixpkgs> {{}}; callPackage {expression_path} {{}}"
        f.write(expr)
        f.flush()
        query_cmd = ["nix-env", "-qa", "*", "--json", "-f", str(f.name)]
        out = subprocess.check_output(query_cmd).strip()
        raw_pkgs = json.loads(out)
        pkgs = {}
        for name, pkg in raw_pkgs.items():
            pkg["_attr"] = name
            pkgs[f"nur.repos.{repo}.{name}"] = pkg
        return pkgs


def index_command(args: Namespace) -> None:
    manifest_path = ROOT.joinpath("repos.json")
    with open(manifest_path) as f:
        manifest = json.load(f)
    repos = manifest.get("repos", [])
    pkgs: Dict[str, Any] = {}

    for (repo, data) in repos.items():
        pkgs.update(index_repo(repo, data.get("file", "default.nix")))

    with open(ROOT.joinpath("packages.json"), "w") as f:
        json.dump(pkgs, f, indent=4)
