#!/usr/bin/env bash

set -x -eu -o pipefail # Exit with nonzero exit code if anything fails

if [[ "$TRAVIS_EVENT_TYPE" == "cron" ]] || [[ "$TRAVIS_EVENT_TYPE" == "api" ]]; then
  keys_dir=$(mktemp -d)
  openssl aes-256-cbc \
    -K $encrypted_080f214a372c_key \
    -iv $encrypted_080f214a372c_iv \
    -in ci/keys.tar.gz.enc -out ci/keys.tar.gz -d
  tar -C "$keys_dir" -xzvf ci/keys.tar.gz

  eval "$(ssh-agent -s)"

  chmod 600 "${keys_dir}/ssh-key"
  ssh-add "${keys_dir}/ssh-key"
  gpg --import "${keys_dir}/gpg-private-key"
  rm -rf "$keys_dir"
fi

export encrypted_080f214a372c_key= encrypted_080f214a372c_iv=

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

git config --global user.name "Nur a bot"
git config --global user.email "joerg.nur-bot@thalheim.io"
git config --global user.signingkey "B4E40EEC9053254E"
git config --global commit.gpgsign true

git clone git@github.com:nix-community/nur-channel

./bin/nur build-channel nur-channel

if [[ -z "$(git diff --exit-code)" ]]; then
  echo "No changes to the output on this push; exiting."
else
  git add --all repos.json*

  git commit -m "automatic update"
  git push git@github.com:nix-community/NUR HEAD:master
fi

(cd nur-channel && git push origin master)
