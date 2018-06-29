#!/usr/bin/env bash

set -eux -o pipefail # Exit with nonzero exit code if anything fails

python ./nur/update.py
nix-build

# Pull requests and commits to other branches shouldn't try to deploy, just build to verify
if [[ "$TRAVIS_EVENT_TYPE" != "cron" ]]; then
  echo "Skipping deploy; just doing a build."
  exit 0
fi

git config user.name "Travis CI"
git config user.email "travis@travis.org"

if [ -z "$(git diff --exit-code)" ]; then
  echo "No changes to the output on this push; exiting."
  exit 0
fi

git add --all repos.json*

git commit -m "automatic update"
git push git@github.com:nix-community/NUR master
