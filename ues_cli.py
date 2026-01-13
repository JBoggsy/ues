#!/usr/bin/env python3
"""Command-line interface for User Environment Simulator (UES).

This module provides CLI commands to start and manage the UES server.

Usage:
    ues --help                     Show help
    ues server                     Start the API server (development mode)
    ues server --host 0.0.0.0      Start server on all interfaces
    ues server --port 8080         Start server on custom port
    ues server --reload            Enable auto-reload for development
    ues version                    Show version information

Examples:
    # Start development server with auto-reload
    ues server --reload
    
    # Start production server
    ues server --host 0.0.0.0 --port 8000
    
    # Quick start (alias)
    ues-server
"""

import argparse
import sys
from typing import Optional


def get_version() -> str:
    """Get the current UES version.
    
    Returns:
        Version string from package metadata or fallback.
    """
    try:
        from models.version import UES_VERSION
        return UES_VERSION
    except ImportError:
        return "0.1.0-dev"


def run_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = False,
    workers: Optional[int] = None,
) -> None:
    """Start the UES API server using uvicorn.
    
    Args:
        host: Host interface to bind to.
        port: Port number to listen on.
        reload: Enable auto-reload for development.
        workers: Number of worker processes (production only).
    """
    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn is not installed.", file=sys.stderr)
        print("Install it with: pip install ues[server]", file=sys.stderr)
        sys.exit(1)
    
    print(f"🚀 Starting UES API Server v{get_version()}")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Reload: {reload}")
    if workers:
        print(f"   Workers: {workers}")
    print()
    print(f"📖 API Documentation: http://{host}:{port}/docs")
    print(f"📖 ReDoc: http://{host}:{port}/redoc")
    print()
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers if not reload else None,
    )


def cmd_server(args: argparse.Namespace) -> None:
    """Handle the 'server' command.
    
    Args:
        args: Parsed command-line arguments.
    """
    run_server(
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers,
    )


def cmd_version(args: argparse.Namespace) -> None:
    """Handle the 'version' command.
    
    Args:
        args: Parsed command-line arguments.
    """
    print(f"UES (User Environment Simulator) v{get_version()}")


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI.
    
    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="ues",
        description="User Environment Simulator (UES) - AI-driven testing tool for AI personal assistants",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ues server                    Start the API server (development)
  ues server --reload           Start with auto-reload
  ues server --host 0.0.0.0     Start on all interfaces
  ues version                   Show version information

For more information, visit: https://github.com/jbboggs/ues
        """,
    )
    
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {get_version()}",
    )
    
    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        description="Available commands",
    )
    
    # Server command
    server_parser = subparsers.add_parser(
        "server",
        help="Start the UES API server",
        description="Start the UES REST API server using uvicorn",
    )
    server_parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host interface to bind to (default: 127.0.0.1)",
    )
    server_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )
    server_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    server_parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of worker processes (production only, incompatible with --reload)",
    )
    server_parser.set_defaults(func=cmd_server)
    
    # Version command
    version_parser = subparsers.add_parser(
        "version",
        help="Show version information",
    )
    version_parser.set_defaults(func=cmd_version)
    
    return parser


def main(args: Optional[list[str]] = None) -> None:
    """Main entry point for the UES CLI.
    
    Args:
        args: Command-line arguments (defaults to sys.argv[1:]).
    """
    parser = create_parser()
    parsed_args = parser.parse_args(args)
    
    if parsed_args.command is None:
        parser.print_help()
        sys.exit(0)
    
    # Execute the command's function
    if hasattr(parsed_args, "func"):
        parsed_args.func(parsed_args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
