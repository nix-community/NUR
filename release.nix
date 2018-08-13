{ nixpkgs ? import <nixpkgs> }:

with import <nixpkgs> {};

python3Packages.buildPythonApplication {
  name = "nur";
  src = ./.;

  makeWrapperArgs = [
    "--prefix" "PATH" ":" "${stdenv.lib.makeBinPath [ nix-prefetch-git git nix ]}"
  ];
}
