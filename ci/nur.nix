{
  buildPythonApplication,
  lib,
  nix-prefetch-git,
  aiohttp,
  git,
  nix,
  glibcLocales,
}:

buildPythonApplication {
  name = "nur";
  src = ./.;

  doCheck = false;

  dependencies = [
    aiohttp
  ];

  makeWrapperArgs = [
    "--prefix"
    "PATH"
    ":"
    "${lib.makeBinPath [
      nix-prefetch-git
      git
      nix
    ]}"
    "--set"
    "LOCALE_ARCHIVE"
    "${glibcLocales}/lib/locale/locale-archive"
  ];
}
