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
    parser.add_argument("--question", "-q", required=False, help="Question to ask")
    parser.add_argument("--demo", action="store_true", help="Run in demo mode (Ayaan preselected, greeting prompt)")
    parser.add_argument("--transcripts-only", action="store_true", help="Use only transcripts; skip analyzers and return a polite fallback if insufficient")
    args = parser.parse_args()
    # Prepare arguments for CLI runner
    if args.demo:
        argv = ["cli_runner", "--demo"]
        if args.transcripts_only:
            argv.append("--transcripts-only")
        sys.argv = argv
    else:
        if not args.question:
            print("--question is required unless --demo is used")
            sys.exit(1)
        argv = ["cli_runner", args.question]
        if args.transcripts_only:
            argv.append("--transcripts-only")
        sys.argv = argv
    asyncio.run(cli_main())


if __name__ == "__main__":
    main()
