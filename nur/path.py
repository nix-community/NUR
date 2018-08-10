import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
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
