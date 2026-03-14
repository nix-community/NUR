#!/usr/bin/env nix-shell
#!nix-shell -p git -p nix -p bash -i bash

set -eu -o pipefail # Exit with nonzero exit code if anything fails


DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

source ${DIR}/lib/setup-git.sh
set -x

nix run "${DIR}#" -- update

cd ${DIR}/..

nix flake update nixpkgs

if [[ -z "$(git diff --exit-code)" ]]; then
  echo "No changes to the output on this push; exiting."
else
  git add --all repos.json* flake.lock
  git commit -m "automatic update"
fi
