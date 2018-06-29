#!/usr/bin/env bash

set -eux -o pipefail # Exit with nonzero exit code if anything fails

# Pull requests and commits to other branches shouldn't try to deploy, just build to verify
if [[ "$TRAVIS_PULL_REQUEST" != "false" ]] || \
	[[ "$TRAVIS_BRANCH" != master ]] && \
	[[ "$TRAVIS_BRANCH" != "$(cat .version)" ]]; then
    echo "Skipping deploy; just doing a build."
    python ./nur/update.py
    nix-build
    exit 0
fi

python ./nur/update.py
nix-build

if [ "$TRAVIS_BRANCH" = master ]; then
    git config user.name "Travis CI"
    git config user.email "$COMMIT_AUTHOR_EMAIL"
    
    if [ -z "$(git diff --exit-code)" ]; then
    	echo "No changes to the output on this push; exiting."
    	exit 0
    fi
    
    git add --all repos.json*

    git commit -m "automatic update"
    git push origin master
fi
