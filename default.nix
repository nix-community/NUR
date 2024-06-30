{ nurpkgs ? import <nixpkgs> {} # For nixpkgs dependencies used by NUR itself
  # Dependencies to call NUR repos with
, pkgs ? import <nixpkgs>
  # this override handles the case where NUR is installed via standalone channel or channel + override
  { overrides = [ (final: prev:
      if prev ? nur
      then prev
      else { nur = ./. { pkgs = final; }; }
    ) ]; }
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
