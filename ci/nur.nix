{
  buildPythonApplication,
  lib,
  nix-prefetch-git,
  aiohttp,
  aiodns,
  git,
  nix,
  glibcLocales,
  setuptools,
}:

buildPythonApplication {
  name = "nur";
  src = ./.;
  pyproject = true;
  build-system = [ setuptools ];

  doCheck = false;

  dependencies = [
    aiohttp
    aiodns
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
