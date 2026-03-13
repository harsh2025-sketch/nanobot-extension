{ pkgs ? import <nixpkgs> {} }:
let
  python = pkgs.python311;
in
pkgs.mkShell {
  packages = [
    python
    pkgs.python311Packages.pip
    pkgs.python311Packages.hatchling
    pkgs.python311Packages.virtualenv
  ];

  shellHook = ''
    export NANOBOT_DEV_SHELL=1
    echo "Nanobot dev shell ready."
  '';
}
