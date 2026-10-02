{
  nurpkgs ? import <nixpkgs> { }, # For nixpkgs dependencies used by NUR itself
  # Dependencies to call NUR repos with
  # The override handles the case where NUR is installed via standalone channel or channel + override
  pkgs ? (
    import <nixpkgs> {
      overrides = [
        (final: prev: if prev ? nur then prev else { nur = import ./. { pkgs = final; }; })
      ];
    }
  ),
  repoOverrides ? { },
}:

let
  manifest = (builtins.fromJSON (builtins.readFile ./repos.json)).repos;
  lockedRevisions = (builtins.fromJSON (builtins.readFile ./repos.json.lock)).repos;

  inherit (nurpkgs) lib;

  tryEvalRepo =
    name: fallback: value:
    let
      result = builtins.tryEval value;
    in
    if result.success then
      result.value
    else
      lib.warn "NUR: repository '${name}' failed to evaluate and was skipped" fallback;

  repoSource =
    name: attr:
    import ./lib/repoSource.nix {
      inherit
        name
        attr
        manifest
        lockedRevisions
        lib
        ;
      fetchgit = builtins.fetchGit or nurpkgs.fetchgit;
      fetchzip = builtins.fetchTarball or nurpkgs.fetchzip;
    };

  # https://github.com/nix-community/NUR/issues/916
  # Use Nixpkgs fetchers in repo-sources for compatibility with ci
  repoSource' =
    name: attr:
    import ./lib/repoSource.nix {
      inherit
        name
        attr
        manifest
        lockedRevisions
        lib
        ;
      inherit (nurpkgs) fetchgit fetchzip;
    };

  createRepo =
    name: attr:
    tryEvalRepo name { } (
      import ./lib/evalRepo.nix {
        inherit name pkgs lib;
        inherit (attr) url;
        src = repoSource name attr + ("/" + (attr.file or ""));
      }
    );

in
{
  repos = (lib.mapAttrs createRepo manifest) // repoOverrides;
  repo-sources = lib.mapAttrs repoSource' manifest;
}
