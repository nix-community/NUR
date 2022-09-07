{
  description = "Nix User Repository";

  outputs = { self }: {
    overlay = final: prev: {
      nur = import ./default.nix {
        nurpkgs = prev;
        pkgs = prev;
      };
    };
    nixosModules.nur = { lib, pkgs, ... }: {
      options.nur = lib.mkOption {
        type = lib.mkOptionType {
          name = "nur";
          description = "An instance of the Nix User repository";
          check = builtins.isAttrs;
        };
        description = "Use this option to import packages from NUR";
        default = import self {
          nurpkgs = pkgs;
          pkgs = pkgs;
        };
      };
    };
    hmModules.nur = self.nixosModules.nur;
  };
}
