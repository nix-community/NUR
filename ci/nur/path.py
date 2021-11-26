import os
import subprocess
from pathlib import Path

from .error import NurError


def _is_repo(path: Path) -> bool:
    return path.joinpath("lib/evalRepo.nix").exists()


def _find_root() -> Path:
    source_root = Path(__file__).parent.parent.resolve()
    if _is_repo(source_root):
        # if it was not build with release.nix
        return source_root
    else:
        root = Path(os.getcwd()).resolve()

        while True:
            if _is_repo(root):
                return root
            new_root = root.parent.resolve()
            if new_root == root:
                if _is_repo(new_root):
                    return new_root
                else:
                    raise NurError("NUR repository not found in current directory")
            root = new_root


ROOT = _find_root()
LOCK_PATH = ROOT.joinpath("repos.json.lock")
MANIFEST_PATH = ROOT.joinpath("repos.json")
EVALREPO_PATH = ROOT.joinpath("lib/evalRepo.nix")

_NIXPKGS_PATH = None


def nixpkgs_path() -> str:
    global _NIXPKGS_PATH
    if _NIXPKGS_PATH is not None:
        return _NIXPKGS_PATH
    cmd = ["nix-instantiate", "--find-file", "nixpkgs"]
    path = subprocess.check_output(cmd).decode("utf-8").strip()
    _NIXPKGS_PATH = str(Path(path).resolve())

    return _NIXPKGS_PATH
