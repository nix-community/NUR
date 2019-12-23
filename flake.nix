{
  description = "Nix User Repository";

  epoch = 201909;

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
