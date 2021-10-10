{ buildPythonApplication, lib, nix-prefetch-git, git, nixUnstable, glibcLocales }:

buildPythonApplication {
  name = "nur";
  src = ./.;

  doCheck = false;

  makeWrapperArgs = [
    "--prefix" "PATH" ":" "${lib.makeBinPath [ nix-prefetch-git git nixUnstable ]}"
    "--set" "LOCALE_ARCHIVE" "${glibcLocales}/lib/locale/locale-archive"
  ];
}
