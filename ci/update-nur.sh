#!/usr/bin/env nix-shell
#!nix-shell -p git -p bash -i bash

set -eu -o pipefail # Exit with nonzero exit code if anything fails

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

source ${DIR}/lib/setup-git.sh
set -x

nix run '(import ./release.nix {})' -c nur update
nix-build

git clone \
  --single-branch \
  "https://$API_TOKEN_GITHUB@github.com/nix-community/nur-combined.git"

nix run '(import ./release.nix {})' -c nur combine \
  --irc-notify nur-bot@chat.freenode.net:6697/nixos-nur \
  nur-combined

if [[ -z "$(git diff --exit-code)" ]]; then
  echo "No changes to the output on this push; exiting."
else
  git add --all repos.json*
  git commit -m "automatic update"
  # in case we are getting overtaken by a different job
  git pull --rebase origin master
  git push git@github.com:nix-community/NUR HEAD:master
fi

git -C nur-combined pull --rebase origin master
git -C nur-combined push origin HEAD:master
