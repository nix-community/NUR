with import <nixpkgs> {};
stdenv.mkDerivation {
  name = "env";
  buildInputs = [
    bashInteractive
    hugo
    python3
    python3Packages.requests
  ];
}
