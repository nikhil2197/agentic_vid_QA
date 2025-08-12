#!/usr/bin/env python3
"""
Main entrypoint for Agentic Video QA System CLI
"""

import sys
import argparse
import asyncio
from src.cli_runner import main as cli_main


def main():
    parser = argparse.ArgumentParser(description="Agentic Video QA CLI")
    # Optional positional 'mode' for legacy compatibility ('cli' only)
    parser.add_argument('mode', nargs='?', choices=['cli'], help='Legacy mode specifier (must be "cli"). Can be omitted.', default=None)
    parser.add_argument("--question", "-q", required=True, help="Question to ask")
    args = parser.parse_args()
    # Prepare arguments for CLI runner
    sys.argv = ["cli_runner", args.question]
    asyncio.run(cli_main())


if __name__ == "__main__":
    main()
