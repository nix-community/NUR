# NUR
Nix User Repository: User contributed nix packages

[![Build Status](https://travis-ci.com/nix-community/NUR.svg?branch=master)](https://travis-ci.com/nix-community/NUR)

This should become an index for user contributed package sets.

## Usage

Clone the repo somewhere and then run the `./install-overlay` script. Now you should be able to use the packages described in the repo.

Eg:

    nix run repos.mic92.cntr -c cntr

## Add your own repository

Edit the `repos.json` file and send a pull-request.
