import json
import subprocess
import sys
from argparse import Namespace
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict


def resolve_source(pkg: Dict, repo: str, url: str) -> str:
    # TODO commit hash
    prefix = f"https://github.com/nix-community/nur-combined/tree/master/repos/{repo}"
    position = pkg["meta"].get("position", None)
    if position is not None and position.startswith("/nix/store"):
        path_str, line = position.rsplit(":", 1)
        path = Path(path_str)
        # I've decided to just take these 2 repositories,
        # update this whenever someone decided to use a recipe source other than
        # NUR or nixpkgs to override packages on. right now this is about as accurate as
        # `nix edit` is
        # TODO find commit hash
        prefixes = {
            "nixpkgs": "https://github.com/nixos/nixpkgs/tree/master/",
            "nur": "https://github.com/nix-community/nur-combined/tree/master/",
        }
        stripped = path.parts[4:]
        if path.parts[3].endswith("source"):

            def url_contains(host: str) -> bool:
                return url.find(host) != -1

            canonical_url = url
            if url_contains("github"):
                canonical_url += "/blob/"
            elif url_contains("gitlab"):
                canonical_url += "/-/blob/"
            attrPath = "/".join(stripped)
            location = f"{canonical_url}{attrPath}"
            return f"{location}#L{line}"
        elif stripped[0] not in prefixes:
            print(path, file=sys.stderr)
            print(
                f"we could not find {stripped} , you can file an issue at https://github.com/nix-community/NUR/issues to the indexing file if you think this is a mistake",
                file=sys.stderr,
            )
            return prefix
        else:
            attrPath = "/".join(stripped[1:])
            location = f"{prefixes[stripped[0]]}{attrPath}"
            return f"{location}#L{line}"
    elif position is not None and position.find("nur-combined") > -1:
        path_str, line = position.rsplit(":", 1)
        stripped = path_str.partition(f"nur-combined/repos/{repo}")[2]
        return f"{prefix}{stripped}#L{line}"
    else:
        return prefix


def index_repo(
    directory: Path, repo: str, expression_file: str, url: str
) -> Dict[str, Any]:
    default_nix = directory.joinpath("default.nix").resolve()
    expr = """
with import <nixpkgs> {};
let
  nur = import %s { nurpkgs = pkgs; inherit pkgs; };
in
callPackage (nur.repo-sources."%s" + "/%s") {}
""" % (
        default_nix,
        repo,
        expression_file,
    )

    with NamedTemporaryFile(mode="w") as f:
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
            pkg["meta"]["position"] = resolve_source(pkg, repo, url)
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
        repo_pkgs = index_repo(
            directory,
            repo,
            data.get("file", "default.nix"),
            data.get("url", "https://github.com/nixos/nixpkgs"),
        )
        pkgs.update(repo_pkgs)

    json.dump(pkgs, sys.stdout, indent=4)
