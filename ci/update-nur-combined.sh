#!/usr/bin/env nix-shell
#!nix-shell -p git -p nix -p bash -i bash

set -eu -o pipefail # Exit with nonzero exit code if anything fails


DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

source ${DIR}/lib/setup-git.sh
set -x

cd "${DIR}/.."

nix run "${DIR}#" -- combine nur-combined

git -C nur-combined pull --rebase origin master
git -C nur-combined push origin HEAD:master
