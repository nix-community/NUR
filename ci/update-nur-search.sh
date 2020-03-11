#!/usr/bin/env bash

set -eu -o pipefail # Exit with nonzero exit code if anything fails

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

source ${DIR}/lib/travis-functions.sh

dont-continue-on-pull-requests

source ${DIR}/lib/setup-git.sh


# build package.json for nur-search
# ---------------------------------

nix-build --quiet release.nix

git clone git@github.com:nix-community/nur-search

result/bin/nur index . > nur-search/data/packages.json

# rebuild and publish nur-search repository
# -----------------------------------------

cd nur-search
if [[ ! -z "$(git diff --exit-code)" ]]; then
    git add ./data/packages.json
    git commit -m "automatic update package.json"
    git push origin master
    nix-shell --run "make && make publish"
else
    echo "nothings changed will not commit anything"
fi
