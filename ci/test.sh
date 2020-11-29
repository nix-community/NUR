#!/usr/bin/env nix-shell
#!nix-shell -p bash -i bash -p python3Packages.mypy -p python3Packages.black -p python3Packages.flake8

set -eux -o pipefail # Exit with nonzero exit code if anything fails

nix run '(import ./release.nix {})' -c nur format-manifest
if [ -n "$(git diff --exit-code repos.json)" ]; then
    echo "repos.json was not formatted before committing repos.json:" >&2
    git diff --exit-code repos.json
    echo "Please run ./bin/nur/format-manifest.py and updates repos.json accordingly!" >&2
    exit 1
fi

# Type checker
mypy nur
# Format checker
black --check .
# Linter
flake8 .

nix run '(import ./release.nix {})' -c nur update
nix-build
