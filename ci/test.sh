#!/usr/bin/env nix-shell
#!nix-shell -p bash -i bash -p python3Packages.mypy -p python3Packages.black -p python3Packages.flake8 -p nix

set -eux -o pipefail # Exit with nonzero exit code if anything fails

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

cd "${DIR}"
# Type checker
mypy nur
# Format checker
black --check .
# Linter
flake8 .

cd "${DIR}/.."
nix run "${DIR}#" -- format-manifest
if [ -n "$(git diff --exit-code repos.json)" ]; then
    echo "repos.json was not formatted before committing repos.json:" >&2
    git diff --exit-code repos.json
    echo "Please run ./bin/nur/format-manifest.py and updates repos.json accordingly!" >&2
    exit 1
fi

nix run "${DIR}#" -- update
nix-build
