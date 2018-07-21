# NUR

[![Build Status](https://travis-ci.com/nix-community/NUR.svg?branch=master)](https://travis-ci.com/nix-community/NUR)

The Nix User Repository (NUR) is community-driven meta repository for Nix packages.
It provides access to user repositories that contain package descriptions (Nix
expressions) and allows you to install packages by referencing them via attributes.
In contrast to [Nixpkgs](https://github.com/NixOS/nixpkgs/), packages are built
from source and **are not reviewed by any Nixpkgs member**.

The NUR was created to share new packages from the community in a faster and
more decentralized way.

NUR automatically check its list of repositories and perform evaluation checks
before it propagated the updates.

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

For NixOS add the following to your `/etc/nixos/configuration.nix`:

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
$ nix-shell -p nur.repos.mic92.inxi
nix-shell> inxi
CPU: Dual Core Intel Core i7-5600U (-MT MCP-) speed/min/max: 3061/500/3200 MHz Kernel: 4.14.51 x86_64
Up: 20h 55m Mem: 12628.4/15926.8 MiB (79.3%) HDD: 465.76 GiB (39.3% used) Procs: 409
Shell: bash 4.4.23 inxi: 3.0.10
```

or

```console
$ nix-env -iA nur.repos.mic92.inxi
```

or

```console
# configuration.nix
environment.systemPackages = with pkgs; [
  nur.repos.mic92.inxi
];
```

Each contributor can register their repository under a name and is responsible
for its content.

***NUR does not check repository for malicious content on a regular base and it is
recommend to check expression before installing them.***

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

## How to add your own repository.

First create a repository that contains a `default.nix` in its top-level directory.

DO NOT import packages for example `with import <nixpkgs> {};`.
Instead take all dependency you want to import from Nixpkgs from the given `pkgs` argument.
Each repository should return a set of Nix derivations:

```nix
{ pkgs }:
{
  inxi = pkgs.callPackage ./inxi {};
}
```

In this example `inxi` would be a directory containing a `default.nix`:

```nix
{ stdenv, fetchFromGitHub
, makeWrapper, perl
, dmidecode, file, hddtemp, nettools, iproute, lm_sensors, usbutils, kmod, xlibs
}:

let
  path = [
    dmidecode file hddtemp nettools iproute lm_sensors usbutils kmod
    xlibs.xdpyinfo xlibs.xprop xlibs.xrandr
  ];
in stdenv.mkDerivation rec {
  name = "inxi-${version}";
  version = "3.0.14-1";

  src = fetchFromGitHub {
    owner = "smxi";
    repo = "inxi";
    rev = version;
    sha256 = "0wyv8cqwy7jlv2r3j7w8ri73iywawnaihww39vlpnpjjcz1b37hw";
  };

  installPhase = ''
    install -D -m755 inxi $out/bin/inxi
    install -D inxi.1 $out/man/man1/inxi.1
    wrapProgram $out/bin/inxi \
      --prefix PATH : ${ stdenv.lib.makeBinPath path }
  '';

  buildInputs = [ perl ];
  nativeBuildInputs = [ makeWrapper ];

  meta = with stdenv.lib; {
    description = "System information tool";
    homepage = https://github.com/smxi/inxi;
    license = licenses.gpl3;
    platforms = platforms.linux;
  };
}
```

You can use `nix-shell` or `nix-build` to build your packages:

```console
$ nix-shell --arg pkgs 'import <nixpkgs> {}' -A inxi
nix-shell> inxi
nix-shell> find $buildInputs
```

```console
$ nix-build --arg pkgs 'import <nixpkgs> {}' -A inxi
```

For development convenience, you can also set a default value for the pkgs argument:

```nix
{ pkgs ? import <nixpkgs> {} }:
{
  inxi = pkgs.callPackage ./inxi {};
}
```

```console
$ nix-build -A inxi
```

Add your own repository to in the `repos.json` of NUR:

```console
$ git clone https://github.com/nix-community/NUR
# open and modify repos.json in an editor
```

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

At the moment each URL must point to a git repository. By running `nur/update.py`
the corresponding `repos.json.lock` is updated and the repository is  tested. This will
perform also an evaluation check, which must be passed for your repository. Commit the changed
`repos.json` but NOT `repos.json.lock`

```
$ git add repos.json
$ ./nur/format_manifest.py # ensure repos.json is sorted alphabetically
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
cron job in travis ci to update our lock file `repos.json.lock`.
To update NUR faster, you can use our service at https://nur-update.herokuapp.com/
after you have pushed an update to your repository, e.g.:

```console
curl -XPOST https://nur-update.herokuapp.com/update?repo=mic92
```

Check out the [github page](https://github.com/nix-community/nur-update#nur-update-endpoint) for further details

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

## Roadmap

- Implement a search to find packages
- Figure out how make it working for NixOS modules
