{
  name, attr,
  fetchgit, fetchzip, lib,
  manifest, lockedRevisions
}:

let
  parseGitlabUrl = url: with builtins; let
    parts = lib.splitString "/" url;
    len = length parts;
  in {
    domain = elemAt parts 2;
    # Allow for deeper hierarchies than owner/repo (GL has groups and subgroups)
    path = lib.drop 3 parts;
  };

  revision = lockedRevisions.${name};
  submodules = attr.submodules or false;
  type = attr.type or null;

  localPath = ../repos + "/${name}";
in
  if lib.pathExists localPath then
    localPath
  else if lib.hasPrefix "https://github.com" attr.url && !submodules then
    fetchzip {
      url = "${attr.url}/archive/${revision.rev}.zip";
      inherit (revision) sha256;
    }
  else if (lib.hasPrefix "https://gitlab.com" attr.url || type == "gitlab") && !submodules then
    let
      gitlab = parseGitlabUrl attr.url;
      escapedPath = builtins.concatStringsSep "%2F" gitlab.path;
    in fetchzip {
      url = "https://${gitlab.domain}/api/v4/projects/${escapedPath}/repository/archive.tar.gz?sha=${revision.rev}";
      inherit (revision) sha256;
    }
  else
    fetchgit {
      inherit (attr) url;
      inherit (revision) rev sha256;
      fetchSubmodules = submodules;
    }
