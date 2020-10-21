{ nurpkgs ? import <nixpkgs> {} # For nixpkgs dependencies used by NUR itself
  # Dependencies to call NUR repos with
, pkgs ? null
, repoOverrides ? { }
}:

let
  manifest = (builtins.fromJSON (builtins.readFile ./repos.json)).repos;
  lockedRevisions = (builtins.fromJSON (builtins.readFile ./repos.json.lock)).repos;

  inherit (nurpkgs) lib;

  repoSource = name: attr: import ./lib/repoSource.nix {
    inherit name attr manifest lockedRevisions lib;
    inherit (nurpkgs) fetchgit fetchzip;
  };

  createRepo = name: attr: import ./lib/evalRepo.nix {
    inherit name pkgs lib;
    inherit (attr) url;
    src = repoSource name attr + ("/" + (attr.file or ""));
  };

in {
  repos =  (lib.mapAttrs createRepo manifest) // repoOverrides;
  repo-sources = lib.mapAttrs repoSource manifest;
}
