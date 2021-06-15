# NUR

The Nix User Repository (NUR) is community-driven meta repository for Nix packages.
It provides access to user repositories that contain package descriptions (Nix
expressions) and allows you to install packages by referencing them via attributes.
In contrast to [Nixpkgs](https://github.com/NixOS/nixpkgs/), packages are built
from source and **are not reviewed by any Nixpkgs member**.

The NUR was created to share new packages from the community in a faster and
more decentralized way.

NUR automatically checks its list of repositories and performs evaluation checks
before it propagates the updates.

## Installation

First include NUR in your `packageOverrides`:

To make NUR accessible for your login user, add the following to `~/.config/nixpkgs/config.nix`:

```nix
{
  packageOverrides = pkgs: {
    nur = import (builtins.fetchTarball "https://github.com/nix-community/NUR/archive/master.tar.gz") {
      inherit pkgs;
    };
  };
}
```

For NixOS add the following to your `/etc/nixos/configuration.nix`
Notice: If you want to use NUR in nix-env, home-manager or in nix-shell you also need NUR in `~/.config/nixpkgs/config.nix`
as shown above!

```nix
{
  nixpkgs.config.packageOverrides = pkgs: {
    nur = import (builtins.fetchTarball "https://github.com/nix-community/NUR/archive/master.tar.gz") {
      inherit pkgs;
    };
  };
}
```

### Pinning

Using `builtins.fetchTarball` without a sha256 will only cache the download for 1 hour by default, so you need internet access almost every time you build something. You can pin the version if you don't want that:

```nix
builtins.fetchTarball {
  # Get the revision by choosing a version from https://github.com/nix-community/NUR/commits/master
  url = "https://github.com/nix-community/NUR/archive/3a6a6f4da737da41e27922ce2cfacf68a109ebce.tar.gz";
  # Get the hash by running `nix-prefetch-url --unpack <url>` on the above url
  sha256 = "04387gzgl8y555b3lkz9aiw9xsldfg4zmzp930m62qw8zbrvrshd";
}
```

## How to use

Then packages can be used or installed from the NUR namespace.

```console
$ nix-shell -p nur.repos.mic92.hello-nur
nix-shell> hello
Hello, NUR!
```

or

```console
$ nix-env -f '<nixpkgs>' -iA nur.repos.mic92.hello-nur
```

or

```console
# configuration.nix
environment.systemPackages = with pkgs; [
  nur.repos.mic92.hello-nur
];
```

Each contributor can register their repository under a name and is responsible
for its content.

***NUR does not check the repository for malicious content on a regular basis
and it is recommended to check the expressions before installing them.***

### Using modules overlays or library functions in NixOS

If you intend to use modules, overlays or library functions in your NixOS configuration.nix, you need to take care to not introduce infinite recursion. Specifically, you need to import NUR like this in the modules:

```nix
{ pkgs, config, lib, ... }:
let
  nur-no-pkgs = import (builtins.fetchTarball "https://github.com/nix-community/NUR/archive/master.tar.gz") {};
in {

  imports = [
    nur-no-pkgs.repos.paul.modules.foo
  ];

  nixpkgs.overlays = [
    nur-no-pkgs.repos.ben.overlays.bar
  ];

}
```

### Integrating with Home Manager

Integrating with [Home Manager](https://github.com/rycee/home-manager) can be done by adding your modules to the `imports` attribute.
You can then configure your services like usual.

```nix
let
  nur-no-pkgs = import (builtins.fetchTarball "https://github.com/nix-community/NUR/archive/master.tar.gz") {};
in
{
  imports = lib.attrValues nur-no-pkgs.repos.moredhel.hmModules.modules;

  services.unison = {
    enable = true;
    profiles = {
      org = {
        src = "/home/moredhel/org";
        dest = "/home/moredhel/org.backup";
        extraArgs = "-batch -watch -ui text -repeat 60 -fat";
      };
    };
  };
}
```

### Flake Support

**Experimental** Note that flake support is still experimental and might change in future in a backwards incompatible way.
Using overlays and modules from NUR in your configuration is fairly straight forward.

In your flake.nix:
```nix
{
  inputs.nur.url = github:nix-community/NUR;

  outputs = {self, nixpkgs, nur }:
  {
    nixosConfigurations.myConfig = nixpkgs.lib.nixosSystem {
      # ...
      modules = [
        # this adds a nur attribute set that can be used for example like this:
        #  ({ pkgs, ... }: {
        #    environment.systemPackages = [ pkgs.nur.repos.mic92.hello-nur ];
        #  })
        { nixpkgs.overlays = [ nur.overlay ]; }
      ];
    };
 };
}
```

Using NUR defined modules in your NixOS configuration.nix introduce infinite recursion, you need to add additional imports to prevent it:

```nix
{
  inputs.nur.url = "github:nix-community/NUR";
  outputs = { self, nixpkgs, nur }: rec {
    nixosConfigurations.myConfig = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        { nixpkgs.overlays = [ nur.overlay ]; }
        ({ pkgs, ... }:
          let
            nur-no-pkgs = import nur {
              nurpkgs = import nixpkgs { system = "x86_64-linux"; };
            };
          in {
            imports = [ nur-no-pkgs.repos.paul.modules.foo ];
            ...
         })
      ];
    };
    defaultPackage.x86_64-linux = nixosConfigurations.myConfig.config.system.build.vm;
  };
}
```

## Finding packages

You can find all packages using
[Packages search for NUR](https://nur.nix-community.org/)
or search our
[nur-combined](https://github.com/nix-community/nur-combined)
repository, which contains all nix expressions from all users, via
[github](https://github.com/nix-community/nur-combined/search).

## How to add your own repository.

First create a repository that contains a `default.nix` in its top-level directory.
We also provide [repository template](https://github.com/nix-community/nur-packages-template) that contains
a prepared directory structure.

DO NOT import packages for example `with import <nixpkgs> {};`.
Instead take all dependency you want to import from Nixpkgs from the given `pkgs` argument.
Each repository should return a set of Nix derivations:

```nix
{ pkgs }:
{
  hello-nur = pkgs.callPackage ./hello-nur {};
}
```

In this example `hello-nur` would be a directory containing a `default.nix`:

```nix
{ stdenv, fetchurl, lib }:

stdenv.mkDerivation rec {
  pname = "hello";
  version = "2.10";

  src = fetchurl {
    url = "mirror://gnu/hello/${pname}-${version}.tar.gz";
    sha256 = "0ssi1wpaf7plaswqqjwigppsg5fyh99vdlb9kzl7c9lng89ndq1i";
  };

  postPatch = ''
    sed -i -e 's/Hello, world!/Hello, NUR!/' src/hello.c
  '';

  # fails due to patch
  doCheck = false;

  meta = with lib; {
    description = "A program that produces a familiar, friendly greeting";
    longDescription = ''
      GNU Hello is a program that prints "Hello, world!" when you run it.
      It is fully customizable.
    '';
    homepage = https://www.gnu.org/software/hello/manual/;
    changelog = "https://git.savannah.gnu.org/cgit/hello.git/plain/NEWS?h=v${version}";
    license = licenses.gpl3Plus;
    maintainers = [ maintainers.eelco ];
    platforms = platforms.all;
  };
}
```

You can use `nix-shell` or `nix-build` to build your packages:

```console
$ nix-shell --arg pkgs 'import <nixpkgs> {}' -A hello-nur
nix-shell> hello
nix-shell> find $buildInputs
```

```console
$ nix-build --arg pkgs 'import <nixpkgs> {}' -A hello-nur
```

For development convenience, you can also set a default value for the pkgs argument:

```nix
{ pkgs ? import <nixpkgs> {} }:
{
  hello-nur = pkgs.callPackage ./hello-nur {};
}
```

```console
$ nix-build -A hello-nur
```

Add your own repository to in the `repos.json` of NUR:

```console
$ git clone --depth 1 https://github.com/nix-community/NUR
$ cd NUR
```

edit the file `repos.json`:

```json
{
    "repos": {
        "mic92": {
            "url": "https://github.com/Mic92/nur-packages"
        },
        "<fill-your-repo-name>": {
            "url": "https://github.com/<your-user>/<your-repo>"
        }
    }
}
```

At the moment each URL must point to a git repository. By running `bin/nur update`
the corresponding `repos.json.lock` is updated and the repository is  tested. This will
perform also an evaluation check, which must be passed for your repository. Commit the changed
`repos.json` but NOT `repos.json.lock`

```
$ git add repos.json
$ ./bin/nur format-manifest # ensure repos.json is sorted alphabetically
$ git commit -m "add <your-repo-name> repository"
$ git push
```

and open a pull request towards [https://github.com/nix-community/NUR](https://github.com/nix-community/NUR).

At the moment repositories should be buildable on Nixpkgs unstable. Later we
will add options to also provide branches for other Nixpkgs channels.

### Use a different nix file as root expression

To use a different file instead of `default.nix` to load packages from, set the `file`
option to a path relative to the repository root:

```json
{
    "repos": {
        "mic92": {
            "url": "https://github.com/Mic92/nur-packages",
            "file": "subdirectory/default.nix"
        }
    }
}
```

### Update NUR's lock file after updating your repository

By default we only check for repository updates once a day with an automatic
github action to update our lock file `repos.json.lock`.
To update NUR faster, you can use our service at https://nur-update.herokuapp.com/
after you have pushed an update to your repository, e.g.:

```console
curl -XPOST https://nur-update.herokuapp.com/update?repo=mic92
```

Check out the [github page](https://github.com/nix-community/nur-update#nur-update-endpoint) for further details

### HELP! Why are my NUR packages not updating?
With every build triggered via the URL hook all repositories will be evaluated.Only if the evaluation does not contain errors the repository revision for the user is updated. Typical evaluation errors are:

* Using a wrong license attribute in the metadata.
* Using a builtin fetcher because it will cause access to external URLs during evaluation. Use pkgs.fetch* instead (i.e. instead of `builtins.fetchGit` use `pkgs.fetchgit`)

You can find out if your evaluation succeeded by checking the [latest build job](https://github.com/nix-community/NUR/actions).


### Git submodules

To fetch git submodules in repositories set `submodules`:

```json
{
    "repos": {
        "mic92": {
            "url": "https://github.com/Mic92/nur-packages",
            "submodules": true
        }
    }
}
```

### NixOS modules, overlays and library function support

It is also possible to define more than just packages. In fact any Nix expression can be used.

To make NixOS modules, overlays and library functions more discoverable,
we propose to put them in their own namespace within the repository.
This allows us to make them later searchable, when the indexer is ready.


#### Providing NixOS modules

NixOS modules should be placed in the `modules` attribute:

```nix
{ pkgs }: {
  modules = import ./modules;
}
```

```nix
# modules/default.nix
{
  example-module = ./example-module.nix;
}
```

An example can be found [here](https://github.com/Mic92/nur-packages/tree/master/modules).
Modules should be defined as paths, not functions, to avoid conflicts if imported from multiple locations.

#### Providing Overlays

For overlays use the `overlays` attribute:

```nix
# default.nix
{
  overlays = {
    hello-overlay = import ./hello-overlay;
  };
}
```

```nix
# hello-overlay/default.nix
self: super: {
  hello = super.hello.overrideAttrs (old: {
    separateDebugInfo = true;
  });
}
```

#### Providing library functions

Put reusable nix functions that are intend for public use in the `lib` attribute:

```nix
{ pkgs }:
with pkgs.lib;
{
  lib = {
    hexint = x: hexvals.${toLower x};

    hexvals = listToAttrs (imap (i: c: { name = c; value = i - 1; })
      (stringToCharacters "0123456789abcdef"));
  };
}
```

## Overriding repositories

You can override repositories using `repoOverrides` argument.
This allows to test changes before publishing.

```nix
{
  packageOverrides = pkgs: {
    nur = import (builtins.fetchTarball "https://github.com/nix-community/NUR/archive/master.tar.gz") {
      inherit pkgs;
      repoOverrides = {
        mic92 = import ../nur-packages { inherit pkgs; };
        ## remote locations are also possible:
        # mic92 = import (builtins.fetchTarball "https://github.com/your-user/nur-packages/archive/master.tar.gz") { inherit pkgs; };
      };
    };
  };
}
```

The repo must be a valid package repo, i.e. its root contains a `default.nix` file.

### Overriding repositories with Flake

**Experimental** Note that flake support is still experimental and might change in future in a backwards incompatible way.

You can overide repositories in two ways:

- With packageOverrides 
```nix
{
  inputs.nur.url = "github:nix-community/NUR";
  inputs.paul.url = "path:/some_path/nur-paul"; # example: a local nur.repos.paul for development 

  outputs = {self, nixpkgs, nur, paul }: {
 
  system = "x86_64-linux";
 
  nurpkgs = import nixpkgs { inherit system; };

  ...
  modules = [
       {
         nixpkgs.config.packageOverrides = pkgs: {
            nur = import nur {
              inherit pkgs nurpkgs;
              repoOverrides = { paul = import paul { inherit pkgs; }; };
            };
          };
        }
  ];
  ...
}
```
- With overlay
```nix
{
  modules = [
    {
      nixpkgs.overlays = [
        (final: prev: {
          nur = import nur {
            nurpkgs = prev;
            pkgs = prev;
            repoOverrides = { paul = import paul { pkgs = prev; }; };
          };
        })
      ];
    } 
    ...
  ];
}
```

The **repo must contains** a `flake.nix` file to addition of `default.nix`:  [flake.nix example](https://github.com/Mic92/nur-packages/blob/master/flake.nix) 

- If you need to use NUR defined modules and to avoid infinite recursion complete `nur-no-pkgs` (from previous Flake Support section) as:
```nix
{
  nur-no-pkgs = import nur {
    nurpkgs = import nixpkgs { system = "x86_64-linux"; };
    repoOverrides = { paul = import paul { }; };
  };
}
```

## Contribution guideline

- When adding packages to your repository make sure they build and set
  `meta.broken` attribute to true otherwise.
- Supply meta attributes as described in the [Nixpkgs manual](https://nixos.org/nixpkgs/manual/#sec-standard-meta-attributes), so
  packages can be found by users.
- Keep your repositories slim - they are downloaded by users and our evaluator
  and needs to be hashed.
- Reuse packages from Nixpkgs when applicable, so the binary cache can be
  leveraged

Examples for packages that could be in NUR:

- Packages that are only interesting for a small audience
- Pre-releases
- Old versions of packages that are no longer in Nixpkgs, but needed for legacy reason (i.e. old versions of GCC/LLVM)
- Automatic generated package sets (i.e. generate packages sets from PyPi or CPAN)
- Software with opinionated patches
- Experiments


## Why package sets instead of overlays?

To make it easier to review nix expression NUR makes it obvious where the
package is coming from.
If NUR would be an overlay malicious repositories could
override existing packages.
Also without coordination multiple overlays could easily introduce dependency
cycles.


## Contact

We have a matrix channel on [#nur:nixos.org](https://matrix.to/#/#nur:nixos.org).
Apart from that we also read posts on [https://discourse.nixos.org](https://discourse.nixos.org/).
