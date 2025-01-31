The following points apply when adding a new repository to repos.json

- [ ] I ran `./bin/nur format-manifest` after updating `repos.json` (We will use the same script in github actions to make sure we keep the format consistent)
- [ ] By including this repository in NUR, I confirm that any copyrightable content in the repository (other than built derivations or patches, if applicable) is licensed under the MIT license
- [ ] I confirm that `meta.license` and `meta.sourceProvenance` have been set correctly for any derivations for unfree or not built from source packages

Additionally, the following points are recommended:

- [ ] All applicable `meta` fields have been filled out. See https://nixos.org/manual/nixpkgs/stable/#sec-standard-meta-attributes for more information. The following fields are particularly helpful and can always be filled out:
  - [ ] `meta.description`, so consumers can confirm that that your package is what they're looking for
  - [ ] `meta.license`, even for free packages
  - [ ] `meta.homepage`, for tracking and deduplication
  - [ ] `meta.mainProgram`, so that `nix run` works correctly
