{
  description = "Nix User Repository";

  outputs = { self }: {
    overlay = final: prev: {
      nur = import ./default.nix {
        nurpkgs = prev;
        pkgs = prev;
      };
    };
  };
}
