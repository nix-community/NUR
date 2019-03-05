import argparse
import logging
import sys
from typing import List

from .combine import combine_command
from .format_manifest import format_manifest_command
from .index import index_command
from .path import ROOT
from .update import update_command

LOG_LEVELS = dict(
    debug=logging.DEBUG,
    info=logging.INFO,
    error=logging.ERROR,
    critical=logging.CRITICAL,
)


def parse_arguments(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog=argv[0], description="nur management commands"
    )
    parser.add_argument(
        "--log-level", type=str, default="debug", choices=list(LOG_LEVELS.keys())
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
    logging.basicConfig(level=LOG_LEVELS[args.log_level])

    args.func(args)
