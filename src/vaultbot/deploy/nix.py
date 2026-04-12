"""Nix deployment helper."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NixConfig:
    python_version: str = "python311"
    package_name: str = "vaultbot"


class NixDeployer:
    """Generate Nix deployment configuration."""

    def __init__(self, config: NixConfig | None = None) -> None:
        self._config = config or NixConfig()

    def generate_flake_nix(self) -> str:
        py = self._config.python_version
        name = self._config.package_name
        return (
            "{\n"
            '  description = "VaultBot - Security-first AI agent";\n'
            "\n"
            "  inputs = {\n"
            '    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";\n'
            '    flake-utils.url = "github:numtide/flake-utils";\n'
            "  };\n"
            "\n"
            "  outputs = { self, nixpkgs, flake-utils }:\n"
            "    flake-utils.lib.eachDefaultSystem (system:\n"
            "      let\n"
            "        pkgs = nixpkgs.legacyPackages.$${system};\n"
            f"        python = pkgs.{py};\n"
            "      in {{\n"
            "        packages.default = python.pkgs.buildPythonApplication {{\n"
            f'          pname = "{name}";\n'
            '          version = "0.1.0";\n'
            "          src = ./.;\n"
            '          format = "pyproject";\n'
            "        }};\n"
            "\n"
            "        devShells.default = pkgs.mkShell {{\n"
            "          buildInputs = [ python python.pkgs.pip python.pkgs.pytest ];\n"
            "        }};\n"
            "      }});\n"
            "}\n"
        )

    def generate_shell_nix(self) -> str:
        py = self._config.python_version
        return (
            "{ pkgs ? import <nixpkgs> {} }:\n"
            "pkgs.mkShell {\n"
            "  buildInputs = [\n"
            f"    pkgs.{py}\n"
            f"    pkgs.{py}.pkgs.pip\n"
            f"    pkgs.{py}.pkgs.pytest\n"
            "  ];\n"
            "}\n"
        )
