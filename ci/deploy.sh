#!/usr/bin/env bash

set -eu -o pipefail # Exit with nonzero exit code if anything fails

add-ssh-key() {
  key="$1"
  plain="${key}.plain"
  openssl aes-256-cbc \
    -K $encrypted_025d6e877aa4_key -iv $encrypted_025d6e877aa4_iv \
    -in "$key" -out $plain -d
  chmod 600 "${key}.plain"
  ssh-add "${key}.plain"
  rm "${key}.plain"
}

if [[ "$TRAVIS_EVENT_TYPE" == "cron" ]] || [[ "$TRAVIS_EVENT_TYPE" == "api" ]]; then
  eval "$(ssh-agent -s)"

  add-ssh-key ci/deploy_key.enc
  add-ssh-key ci/deploy_channel_key.enc
fi

export encrypted_025d6e877aa4_key= encrypted_025d6e877aa4_iv=

./bin/nur format-manifest
if [ -n "$(git diff --exit-code repos.json)" ]; then
  echo "repos.json was not formatted before committing repos.json:" >&2
  git diff --exit-code repos.json
  echo "Please run ./nur/format-manifest.py and updates repos.json accordingly!" >&2
  exit 1
fi

./bin/nur update
nix-build

# Pull requests and commits to other branches shouldn't try to deploy, just build to verify
if [[ "$TRAVIS_EVENT_TYPE" != "cron" ]] && [[ "$TRAVIS_EVENT_TYPE" != "api" ]]; then
  echo "Skipping deploy; just doing a build."
  exit 0
fi

git config --global user.name "Travis CI"
git config --global user.email "travis@travis.org"

git clone git@github.com/nix-community/nur-channel

old_channel_rev=$(git rev-parse HEAD)
./bin/nur build-channel nur-channel
new_channel_rev=$(git rev-parse HEAD)

if [[ -z "$(git diff --exit-code)" ]]; then
  echo "No changes to the output on this push; exiting."
else
  git add --all repos.json*

  git commit -m "automatic update"
  git push git@github.com:nix-community/NUR HEAD:master
fi

if [[ $old_channel_rev != $new_channel_rev ]]; then
  (cd nur-channel && git push origin master)
fi
