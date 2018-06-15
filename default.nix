
{ pkgs }:
let
  inherit (pkgs) fetchgit fetchFromGitHub callPackages;
in {
  repos = {
    mic92 = callPackages (fetchFromGitHub {
      owner = "Mic92";
      repo = "nur-packages";
      sha256 = "1pybc9xk415wvw6hhmqs9wwb28g9h2500lv2xj66cjn7sww4adxq";
      rev = "5a16e73333e14b4cb3dbbb1a2e6859f11143b3f2";
    }) {};
  };
}
