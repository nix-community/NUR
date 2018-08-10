import json
import shutil
from argparse import Namespace

from .path import ROOT


def format_manifest_command(args: Namespace) -> None:
    path = ROOT.joinpath("repos.json")
    manifest = json.load(open(path))
    tmp_path = str(path) + ".tmp"
    with open(tmp_path, "w+") as tmp:
        json.dump(manifest, tmp, indent=4, sort_keys=True)
        tmp.write("\n")
    shutil.move(tmp_path, path)
