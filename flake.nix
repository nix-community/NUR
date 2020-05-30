{
  description = "Nix User Repository";

  outputs = { self, nixpkgs }:
    {
      overlay = final: prev: {
        nur = import ./default.nix {
          nurpkgs = nixpkgs;
          pkgs = nixpkgs.pkgs;
        };
      };
    };
}
