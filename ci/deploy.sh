#!/usr/bin/env bash

set -eux -o pipefail # Exit with nonzero exit code if anything fails

if [[ "$TRAVIS_EVENT_TYPE" == "cron" ]]; then
  openssl aes-256-cbc -K $encrypted_025d6e877aa4_key -iv $encrypted_025d6e877aa4_iv -in ci/deploy_key.enc -out deploy_key -d
  chmod 600 deploy_key
  eval "$(ssh-agent -s)"
  ssh-add deploy_key

  # better safe then sorry
  rm deploy_key
fi

unset encrypted_025d6e877aa4_key encrypted_025d6e877aa4_iv

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
git push git@github.com:nix-community/NUR HEAD:master
