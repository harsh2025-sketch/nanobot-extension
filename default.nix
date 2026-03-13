{ pkgs ? import <nixpkgs> {} }:
let
  pyPkgs = pkgs.python311Packages;
in
pyPkgs.buildPythonPackage {
  pname = "nanobot-ai";
  version = "0.1.4";
  format = "pyproject";
  src = ./.;

  nativeBuildInputs = [ pyPkgs.hatchling ];

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
}
