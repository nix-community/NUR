{ nixpkgs ? import <nixpkgs> }:

with import <nixpkgs> {};

python3Packages.buildPythonApplication {
  name = "nur";
  src = ./.;

  # FIXME: uncomment after the next nixpkgs channel bump
  #propagatedBuildInputs = [ python3Packages.irc ];

  # import irc does not work right now.
  doCheck = false;

  makeWrapperArgs = [
    "--prefix" "PATH" ":" "${stdenv.lib.makeBinPath [ nix-prefetch-git git nix ]}"
    "--set" "LOCALE_ARCHIVE" "${glibcLocales}/lib/locale/locale-archive"
  ];
}
