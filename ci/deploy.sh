#!/usr/bin/env bash

set -eu -o pipefail # Exit with nonzero exit code if anything fails

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

source ${DIR}/lib/travis-functions.sh
source ${DIR}/lib/setup-git.sh

nix-build --quiet release.nix

if ! is-automatic-update; then
  bash $DIR/lint.sh
fi

set -x

result/bin/nur update
nix-build

dont-continue-on-pull-requests

git clone git@github.com:nix-community/nur-combined

result/bin/nur combine \
  --irc-notify nur-bot@chat.freenode.net:6697/nixos-nur \
  nur-combined

if [[ -z "$(git diff --exit-code)" ]]; then
  echo "No changes to the output on this push; exiting."
else
  git add --all repos.json*
  git commit -m "automatic update"
  git push git@github.com:nix-community/NUR HEAD:master
fi

(cd nur-combined && git push origin master)
