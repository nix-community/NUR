#!/usr/bin/env bash

set -eu -o pipefail # Exit with nonzero exit code if anything fails

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

is-automatic-update() {
  [[ "$TRAVIS_EVENT_TYPE" == "cron" ]] || [[ "$TRAVIS_EVENT_TYPE" == "api" ]]
}

if is-automatic-update; then
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

nix-build release.nix

if ! is-automatic-update; then
  bash $DIR/lint.sh
fi

result/bin/nur update
nix-build

if ! is-automatic-update; then
  # Pull requests and commits to other branches shouldn't try to deploy, just build to verify
  echo "Skipping deploy; just doing a build."
  exit 0
fi

git config --global user.name "Nur a bot"
git config --global user.email "joerg.nur-bot@thalheim.io"
git config --global user.signingkey "B4E40EEC9053254E"
git config --global commit.gpgsign true

git clone git@github.com:nix-community/nur-combined

result/bin/nur combine \
  --irc-notify nur-bot@chat.freenode.net:6697/nixos-nur nur-combined

if [[ -z "$(git diff --exit-code)" ]]; then
  echo "No changes to the output on this push; exiting."
else
  git add --all repos.json*

  git commit -m "automatic update"
  git push git@github.com:nix-community/NUR HEAD:master
fi

(cd nur-combined && git push origin master)
