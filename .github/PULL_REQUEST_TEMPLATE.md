The following points apply when adding a new repository to repos.json

- [ ] I ran `./bin/nur format-manifest` after updating `repos.json` (We will use the same script in github actions to make sure we keep the format consistent)
- [ ] By including this repository in NUR I give permission to license the
content under the MIT license.

Clarification where license should apply:
The license above does not apply to the packages built by the
Nix Packages collection, merely to the package descriptions (i.e., Nix
expressions, build scripts, etc.).  It also might not apply to patches
included in Nixpkgs, which may be derivative works of the packages to
which they apply. The aforementioned artifacts are all covered by the
licenses of the respective packages.
