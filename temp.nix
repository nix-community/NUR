with import <nixpkgs> {};
let
  nur = import ./. { inherit pkgs;};
in
  callPackage (nur.repo-sources.crazazy + "/pkgs/default.nix")
