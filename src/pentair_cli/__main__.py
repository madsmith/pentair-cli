"""Entry point for CLI execution."""

from __future__ import annotations

from pentair_cli.cli import cli


def main() -> None:
    cli(prog_name="pentair-cli")


if __name__ == "__main__":
    main()
