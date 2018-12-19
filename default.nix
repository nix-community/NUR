{ nurpkgs ? import <nixpkgs> {} # For nixpkgs dependencies used by NUR itself
  # Dependencies to call NUR repos with
, pkgs ? null
  # Overrides over normal NUR repos (e.g. development clones)
, repoOverrides ? {} }:

let
  inherit (nurpkgs) lib;

  manifest = (builtins.fromJSON (builtins.readFile ./repos.json)).repos //
    lib.mapAttrs (_: attr: removeAttrs attr ["lock"]) repoOverrides;
  lockedRevisions = (builtins.fromJSON (builtins.readFile ./repos.json.lock)).repos //
    lib.mapAttrs (_: attr: { inherit (attr) submodules url; } // attr.lock or {}) repoOverrides;

  repoSource = name: attr: import ./lib/repoSource.nix {
    inherit name attr manifest lockedRevisions lib;
    inherit (nurpkgs) fetchgit fetchzip;
  };

  createRepo = name: attr: import ./lib/evalRepo.nix {
    inherit name pkgs lib;
    inherit (attr) url;
    src = repoSource name attr + "/" + (attr.file or "");
  };

in {
  repos =  lib.mapAttrs createRepo manifest;
  repo-sources = lib.mapAttrs repoSource manifest;
}
