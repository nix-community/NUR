#!/usr/bin/env nix-shell
#!nix-shell -p git -p nix -p bash -i bash

set -eu -o pipefail # Exit with nonzero exit code if anything fails

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

source ${DIR}/lib/setup-git.sh
set -x


# build package.json for nur-search
# ---------------------------------

nix-build --quiet release.nix

git clone --single-branch "https://$API_TOKEN_GITHUB@github.com/nix-community/nur-combined.git"

git clone --recurse-submodules "https://$API_TOKEN_GITHUB@github.com/nix-community/nur-search.git"

nix run '(import ./release.nix {})' -c nur index nur-combined > nur-search/data/packages.json

# rebuild and publish nur-search repository
# -----------------------------------------

cd nur-search
if [[ ! -z "$(git diff --exit-code)" ]]; then
    git add ./data/packages.json
    git commit "Nur a bot <joerg.nur-bot@thalheim.io>" -m "automatic update package.json"
    git pull --rebase origin master
    git push origin master
    nix-shell --run "make clean && make && make publish"
else
    echo "nothings changed will not commit anything"
fi
