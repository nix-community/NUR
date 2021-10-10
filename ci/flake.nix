{
  description = "Internal flake for ci tasks of NUR";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  inputs.flake-utils.url = "github:numtide/flake-utils";

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system: {
      packages.nur = nixpkgs.legacyPackages.${system}.python3.pkgs.callPackage ./nur.nix {};
      defaultPackage = self.packages.${system}.nur;
    });
}
