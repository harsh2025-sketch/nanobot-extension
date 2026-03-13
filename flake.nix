{
  description = "Nanobot - personal AI assistant (Nix build + dev shell)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        python = pkgs.python311;
        pyPkgs = pkgs.python311Packages;
      in
      {
        packages.default = pyPkgs.buildPythonPackage {
          pname = "nanobot-ai";
          version = "0.1.4";
          format = "pyproject";
          src = ./.;

          nativeBuildInputs = [ pyPkgs.hatchling ];

          # Core runtime deps available in nixpkgs. Optional channel deps can be
          # installed via pip in the dev shell if needed.
          propagatedBuildInputs = [
            pyPkgs.typer
            pyPkgs.pydantic
            pyPkgs.pydantic-settings
            pyPkgs.websockets
            pyPkgs.websocket-client
            pyPkgs.httpx
            pyPkgs.loguru
            pyPkgs.readability-lxml
            pyPkgs.rich
            pyPkgs.croniter
            pyPkgs.python-telegram-bot
            pyPkgs.lark-oapi
            pyPkgs.socksio
            pyPkgs.python-socketio
            pyPkgs.msgpack
            pyPkgs.slack-sdk
            pyPkgs.prompt-toolkit
            pyPkgs.json-repair
          ];

          pythonImportsCheck = [ "nanobot" ];
        };

        devShells.default = pkgs.mkShell {
          packages = [
            python
            pyPkgs.pip
            pyPkgs.hatchling
            pyPkgs.virtualenv
          ];

          shellHook = ''
            export NANOBOT_DEV_SHELL=1
            echo "Nanobot dev shell ready."
          '';
        };
      }
    );
}
