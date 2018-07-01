
{ pkgs ? import <nixpkgs> {} }:
let
  inherit (pkgs) fetchgit fetchzip callPackages lib;

  manifest = (builtins.fromJSON (builtins.readFile ./repos.json)).repos;
  lockedRevisions = (builtins.fromJSON (builtins.readFile ./repos.json.lock)).repos;

  repoSource = name: attr:
    let
      revision = lockedRevisions.${name};
    in if lib.hasPrefix "https://github.com" attr.url then
      fetchzip {
        url = "${attr.url}/archive/${revision.rev}.zip";
        inherit (revision) sha256;
      }
    else
      fetchgit {
        inherit (attr) url;
        inherit (revision) rev sha256;
      };

   expressionPath = name: attr: (repoSource name attr) + "/" + (attr.file or "");

   createRepo = (name: attr: callPackages (expressionPath name attr) {});
in {
  repos = lib.mapAttrs createRepo manifest;
}
