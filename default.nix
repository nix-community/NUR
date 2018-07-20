{ nurpkgs ? import <nixpkgs> {} # For nixpkgs dependencies used by NUR itself
  # Dependencies to call NUR repos with
, pkgs ? null }:

let
  inherit (nurpkgs) fetchgit fetchzip lib;

  manifest = (builtins.fromJSON (builtins.readFile ./repos.json)).repos;
  lockedRevisions = (builtins.fromJSON (builtins.readFile ./repos.json.lock)).repos;

  parseGitlabUrl = url:
    with builtins;
    let
      parts = lib.splitString "/" url;
      len = length parts;
    in {
      domain = elemAt parts 2;
      owner = elemAt parts (len - 2);
      repo = elemAt parts (len - 1);
    };

  repoSource = name: attr:
    let
      revision = lockedRevisions.${name};
      submodules = attr.submodules or false;
      type = attr.type or null;
    in if lib.hasPrefix "https://github.com" attr.url && !submodules then
      fetchzip {
        url = "${attr.url}/archive/${revision.rev}.zip";
        inherit (revision) sha256;
      }
    else if (lib.hasPrefix "https://gitlab.com" attr.url || type == "gitlab") && !submodules then
      let
        gitlab = parseGitlabUrl attr.url;
      in fetchzip {
        url = "https://${gitlab.domain}/api/v4/projects/${gitlab.owner}%2F${gitlab.repo}/repository/archive.tar.gz?sha=${revision.rev}";
        inherit (revision) sha256;
      }
    else
      fetchgit {
        inherit (attr) url;
        inherit (revision) rev sha256;
        fetchSubmodules = submodules;
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
