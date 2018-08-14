{ name
, url
, src
, pkgs # Do not use this for anything other than passing it along as an argument to the repository
, lib
}:
let

  prettyName = "[32;1m${name}[0m";

  # Arguments passed to each repositories default.nix
  passedArgs = {
    pkgs = if pkgs != null then pkgs else throw ''
      NUR import call didn't receive a pkgs argument, but the evaluation of NUR's ${prettyName} repository requires it.

      This is either because
        - You're trying to use a [1mpackage[0m from that repository, but didn't pass a `pkgs` argument to the NUR import.
          In that case, refer to the installation instructions at https://github.com/nix-community/nur#installation on how to properly import NUR

        - You're trying to use a [1mmodule[0m/[1moverlay[0m from that repository, but it didn't properly declare their module.
          In that case, inform the maintainer of the repository: ${url}
    '';
  };

  expr = import src;
  args = builtins.functionArgs expr;
  # True if not all arguments are either passed by default (e.g. pkgs) or defaulted (e.g. foo ? 10)
  usesCallPackage = ! lib.all (arg: lib.elem arg (lib.attrNames passedArgs) || args.${arg}) (lib.attrNames args);

in if usesCallPackage then throw ''
    NUR repository ${prettyName} is using the deprecated callPackage syntax which
    might result in infinite recursion when used with NixOS modules.
  '' else expr (builtins.intersectAttrs args passedArgs)
