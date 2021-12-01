{ buildPythonApplication, lib, nix-prefetch-git, git, nix, glibcLocales }:

buildPythonApplication {
  name = "nur";
  src = ./.;

  doCheck = false;

  makeWrapperArgs = [
    "--prefix" "PATH" ":" "${lib.makeBinPath [ nix-prefetch-git git nix ]}"
    "--set" "LOCALE_ARCHIVE" "${glibcLocales}/lib/locale/locale-archive"
  ];
}
