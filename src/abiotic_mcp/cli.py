"""Command line entry point."""

import argparse
import shutil
import subprocess
import sys

from . import __version__, doctor, installer


def _register_client():
    client = shutil.which("claude")
    command = shutil.which("abiotic-mcp")
    if client is None or command is None:
        return False
    result = subprocess.run([client, "mcp", "add", "abiotic", "--", command, "serve"], capture_output=True, text=True)
    return result.returncode == 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="abiotic-mcp", description="MCP server for the Abiotic Factor Mod Editor")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "command",
        nargs="?",
        default="serve",
        choices=["serve", "install", "uninstall", "doctor", "config"],
        help="serve (default) runs the MCP server on stdio",
    )
    args = parser.parse_args(argv)

    if args.command == "serve":
        from .server import main as serve

        serve()
    elif args.command == "install":
        installer.install()
        if _register_client():
            print("Registered with the claude CLI as 'abiotic'.")
        else:
            print("Add this to your MCP client config:")
            print(installer.client_config())
        print("Restart the Mod Editor, then run: abiotic-mcp doctor")
    elif args.command == "uninstall":
        installer.uninstall()
    elif args.command == "doctor":
        return 0 if doctor.run() else 1
    elif args.command == "config":
        print(installer.client_config())
    return 0


if __name__ == "__main__":
    sys.exit(main())
