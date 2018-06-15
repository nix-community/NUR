
{ pkgs }:
let
  inherit (pkgs) fetchgit fetchFromGitHub callPackages;
in {
  repos = {
    mic92 = callPackages (fetchFromGitHub {
      owner = "Mic92";
      repo = "nur-packages";
      sha256 = "0j18d3hfsy00kf2y8xp4w7bkv3wkj96vxd8pajcqqykysva44y9g";
      rev = "bcfe13fe3767f7cbd9821f7bb37a1b225d768159";
    }) {};
  };
}
