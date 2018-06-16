
{ pkgs ? import <nixpkgs> {} }:
let
  inherit (pkgs) fetchgit fetchFromGitHub callPackages;
in {
  repos = {
    mic92 = callPackages (fetchFromGitHub {
      owner = "Mic92";
      repo = "nur-packages";
      sha256 = "1sk41q80z6rzrnnzbpkj9jmr9qcsxvh92q7v1jl60f5ms4q0ipx2";
      rev = "8d61d40bf8e17555e81eeabfa7e5d4ac6e01ac37";
    }) {};
  };
}
