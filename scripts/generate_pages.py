#!/usr/bin/env python3

import json
import os
import shutil
from pathlib import Path
from typing import Any, DefaultDict, Dict, List
import requests

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

<style>
table td {{
overflow-wrap: break-word;
}}
</style>

Name | Attribute | Description
-----|-----------|------------
"""
        )
        for pkg in pkgs:
            name = pkg.metadata["name"]
            meta = pkg.metadata["meta"]
            description = meta.get("description")
            if description is None:
                description = ""

            description = description.replace("\n", "")
            homepage = meta.get("homepage", None)
            attribute = pkg.attribute

            if homepage is not None:
                name = f"[{name}]({homepage})"

            location = meta.get("position", None)
            if location is not None:
                attribute = f"[{attribute}]({location})"

            f.write(f"{name}|{attribute}|{description}\n")

def download_readme():
    url = "https://raw.githubusercontent.com/nix-community/NUR/master/README.md"
    r = requests.get(url)
    with open("content/documentation/_index.md", 'wb') as f:
        fm = bytes("""
+++
title = "Documentation"
weight = 1
alwaysopen = true
+++
""", 'utf-8')
        f.write(fm)
        f.write(r.content)

def create_repos_section():
    repos_path = ROOT.joinpath("content", "repos")
    shutil.rmtree(repos_path, ignore_errors=True)
    os.makedirs(repos_path)
    with open(repos_path.joinpath("_index.md"), "w+") as f:
        f.write("""
+++
title = "Repos"
weight = 10
alwaysopen = true
+++
# Repo index

""")

def main() -> None:

    download_readme()

    with open(ROOT.joinpath("data", "packages.json")) as f:
        repos: DefaultDict[str, List[Package]] = DefaultDict(list)
        packages = json.load(f)
        pkg_count = 0
        for attribute, pkg in packages.items():
            pkg_count += 1
            repos[pkg["_repo"]].append(Package(attribute, pkg))

        repos_path = ROOT.joinpath("content", "repos")
        create_repos_section()

        repo_count = 0
        for repo_name, pkgs in repos.items():
            repo_count += 1
            write_repo_page(repos_path, repo_name, pkgs)

        stats_dict={'repo_count':repo_count, 'pkg_count': pkg_count}
        stats_path = ROOT.joinpath("data", "stats.json")
        with open(stats_path, "w+") as f:
            f.write(json.dumps(stats_dict))

if __name__ == "__main__":
    main()
