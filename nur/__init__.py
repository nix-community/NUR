import argparse
import sys
from typing import List

from .format_manifest import format_manifest_command
from .index import index_command
from .update import update_command
from .path import ROOT

from .combine import combine_command


def parse_arguments(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog=argv[0], description="nur management commands"
    )

    subparsers = parser.add_subparsers(description="subcommands")

    combine = subparsers.add_parser("combine")
    combine.add_argument("directory")
    combine.set_defaults(func=combine_command)

    format_manifest = subparsers.add_parser("format-manifest")
    format_manifest.set_defaults(func=format_manifest_command)

    update = subparsers.add_parser("update")
    update.set_defaults(func=update_command)

    index = subparsers.add_parser("index")
    index.add_argument("directory", default=ROOT)
    index.set_defaults(func=index_command)

    args = parser.parse_args(argv[1:])

    if not hasattr(args, "func"):
        print("subcommand is missing", file=sys.stderr)
        parser.print_help(sys.stderr)
        sys.exit(1)

    return args


def main() -> None:
    args = parse_arguments(sys.argv)
    args.func(args)
