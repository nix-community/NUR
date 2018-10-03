#!/usr/bin/env python3

import json
import os
import shutil
from pathlib import Path
from typing import Any, DefaultDict, Dict, List

ROOT = Path(__file__).parent.parent.resolve()


class Package:
    def __init__(self, attribute: str, metadata: Dict[str, Any]) -> None:
        self.attribute = attribute
        self.metadata = metadata


def write_repo_page(repos_path: Path, repo_name: str, pkgs: List[Package]):
    with open(str(repos_path.joinpath(repo_name)) + ".md", "w+") as f:
        f.write(
            f"""
+++
title = "{repo_name}"
+++

# Packages

Name | Attribute | Description
-----|-----------|------------
"""
        )
        for pkg in pkgs:
            name = pkg.metadata["name"]
            meta = pkg.metadata["meta"]

            description = meta.get("description", "").replace("\n", "")
            homepage = meta.get("homepage", None)
            attribute = pkg.attribute

            if homepage is not None:
                name = f"[{name}]({homepage})"

            location = meta.get("position", None)
            if location is not None:
                attribute = f"[{attribute}]({location})"

            f.write(f"{name}|{attribute}|{description}\n")


def main() -> None:
    with open(ROOT.joinpath("data", "packages.json")) as f:
        repos: DefaultDict[str, List[Package]] = DefaultDict(list)
        packages = json.load(f)
        for attribute, pkg in packages.items():
            repos[pkg["_repo"]].append(Package(attribute, pkg))

        repos_path = ROOT.joinpath("content", "repos")
        shutil.rmtree(repos_path, ignore_errors=True)
        os.makedirs(repos_path)
        with open(repos_path.joinpath("_index.md"), "w+") as f:
            f.write("+++\ntitle=\"Repos\"\n+++\n# Repo index")

        for repo_name, pkgs in repos.items():
            write_repo_page(repos_path, repo_name, pkgs)


if __name__ == "__main__":
    main()
