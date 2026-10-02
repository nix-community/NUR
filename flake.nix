{
  description = "Nix User Repository";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
    flake-parts = {
      url = "github:hercules-ci/flake-parts";
      inputs.nixpkgs-lib.follows = "nixpkgs";
    };
  };

  outputs =
    inputs@{ flake-parts, nixpkgs, ... }:
    let
      inherit (nixpkgs) lib;
      manifest = (builtins.fromJSON (builtins.readFile ./repos.json)).repos;
      overlay = final: prev: {
        nur = import ./default.nix {
          nurpkgs = prev;
          pkgs = prev;
        };
      };

      lockedRevisions = (builtins.fromJSON (builtins.readFile ./repos.json.lock)).repos;
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
          fetchgit = builtins.fetchGit or lib.id;
          fetchzip = builtins.fetchTarball or lib.id;
        };
      # Lazily evaluate each repo with pkgs = null; the result is only forced
      # when a specific repo's attribute is accessed.
      repos = lib.mapAttrs (
        name: attr:
        import ./lib/evalRepo.nix {
          inherit name lib;
          inherit (attr) url;
          src = repoSource name attr + ("/" + (attr.file or ""));
          pkgs = null;
        }
      ) manifest;
    in
    flake-parts.lib.mkFlake { inherit inputs; } (
      { moduleLocation, ... }:
      let
        inherit (lib)
          mapAttrs
          mkOption
          types
          ;
        inherit (lib.strings) escapeNixIdentifier;

        # Inlined from flake-parts' module publication helper because we need
        # the same behavior under flake.repos.<name>.modules rather than
        # flake.modules.
        # Ref: https://github.com/hercules-ci/flake-parts/blob/f20dc5d9b8027381c474144ecabc9034d6a839a3/extras/modules.nix
        addRepoModuleInfo =
          repoName: class: moduleName: module:
          { ... }:
          {
            _class = class;
            _file = "${toString moduleLocation}#repos.${escapeNixIdentifier repoName}.modules.${escapeNixIdentifier class}.${escapeNixIdentifier moduleName}";
            imports = [ module ];
          };

        repoModuleOption =
          repoName: class:
          mkOption {
            type = types.lazyAttrsOf types.deferredModule;
            default = { };
            description = "Published ${class} modules for repo `${repoName}`.";
            apply = mapAttrs (addRepoModuleInfo repoName class);
          };

        # Inlined from flake-parts' flake.overlays option so repos.<name>.overlays
        # uses the same named-overlay contract and merge behavior.
        # Ref: https://github.com/hercules-ci/flake-parts/blob/f20dc5d9b8027381c474144ecabc9034d6a839a3/modules/overlays.nix
        repoOverlayType = types.uniq (
          types.functionTo (types.functionTo (types.lazyAttrsOf types.unspecified))
        );
      in
      {
        options = {
          flake.repos = mkOption {
            type = types.lazyAttrsOf (
              types.submodule (
                { name, ... }:
                let
                  darwinModules = repoModuleOption name "darwin";
                  flakeModules = repoModuleOption name "flake";
                  homeModules = repoModuleOption name "homeManager";
                  nixosModules = repoModuleOption name "nixos";
                in
                {
                  options = {
                    inherit
                      darwinModules
                      flakeModules
                      homeModules
                      nixosModules
                      ;
                    modules = {
                      darwin = darwinModules;
                      flake = flakeModules;
                      homeManager = homeModules;
                      nixos = nixosModules;
                    };
                    overlays = mkOption {
                      # uniq -> ordered: https://github.com/NixOS/nixpkgs/issues/147052
                      # also update description when done
                      type = types.lazyAttrsOf repoOverlayType;
                      # This eta expansion exists for the sole purpose of making nix flake check happy.
                      apply = mapAttrs (_k: f: final: prev: f final prev);
                      default = { };
                      description = ''
                        Named overlays published by the repo.

                        The overlays themselves are not mergeable. While overlays
                        can be composed, the order of composition is significant,
                        but the module system does not guarantee sufficiently
                        deterministic definition ordering, across versions and
                        when changing `imports`.
                      '';
                    };
                  };
                }
              )
            );
            default = { };
            description = ''
              Published repository metadata for NUR repos.

              Each repo exposes typed `modules` and `overlays` attributes.
            '';
          };
        };

        config = {
          systems = builtins.filter (
            system: builtins.hasAttr system nixpkgs.legacyPackages
          ) nixpkgs.lib.platforms.all;
          flake = {
            overlays = {
              default = overlay;
            };
            modules = lib.genAttrs [ "nixos" "homeManager" "darwin" ] (_: {
              default = {
                nixpkgs.overlays = [ overlay ];
              };
            });
            repos = mapAttrs (
              name: r:
              let
                darwinModules = r.darwinModules or { };
                flakeModules = r.flakeModules or { };
                homeModules = r.homeModules or r.modules or { };
                nixosModules = r.nixosModules or r.modules or { };
              in
              {
                inherit
                  darwinModules
                  flakeModules
                  homeModules
                  nixosModules
                  ;
                modules = {
                  darwin = darwinModules;
                  flake = flakeModules;
                  homeManager = homeModules;
                  nixos = nixosModules;
                };
                overlays = r.overlays or { };
              }
            ) repos;
          };
          perSystem =
            { pkgs, ... }:
            {
              formatter = pkgs.treefmt.withConfig {
                runtimeInputs = with pkgs; [
                  nixfmt-rfc-style
                ];

                settings = {
                  on-unmatched = "info";
                  tree-root-file = "flake.nix";

                  formatter = {
                    nixfmt = {
                      command = "nixfmt";
                      includes = [ "*.nix" ];
                    };
                  };
                };
              };
              # legacyPackages is used because nur is a package set
              # This trick with the overlay is used because it allows NUR packages to depend on other NUR packages
              legacyPackages = (pkgs.extend overlay).nur;
            };
        };
        imports = [
          inputs.flake-parts.flakeModules.modules
        ];
      }
    );
}
