#!/usr/bin/env python3
"""
Main entry point for Agentic Video QA System
Supports CLI, API, and Gradio frontend modes
"""

import sys
import argparse
import uvicorn
import asyncio
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(
        description="Agentic Video QA System - AI-powered preschool video analysis"
    )
    parser.add_argument(
        "mode",
        choices=["cli", "api", "gradio"],
        help="Mode to run: cli (command line), api (FastAPI server), or gradio (web interface)"
    )
    parser.add_argument(
        "--question", "-q",
        help="Question to ask (for CLI mode)",
        default=""
    )
    parser.add_argument(
        "--host",
        help="Host for API server (default: 0.0.0.0)",
        default="0.0.0.0"
    )
    parser.add_argument(
        "--port",
        help="Port for API server (default: 8000)",
        type=int,
        default=8000
    )
    parser.add_argument(
        "--gradio-port",
        help="Port for Gradio frontend (default: 7860)",
        type=int,
        default=7860
    )
    
    args = parser.parse_args()
    
    if args.mode == "cli":
        if not args.question:
            print("Error: Question is required for CLI mode")
            print("Usage: python main.py cli --question 'Your question here'")
            sys.exit(1)
        
        # Run CLI mode
        from src.cli_runner import main as cli_main
        # Modify sys.argv to pass the question
        sys.argv = ["cli_runner", args.question]
        asyncio.run(cli_main())
        
    elif args.mode == "api":
        # Run FastAPI server
        print(f"Starting FastAPI server on {args.host}:{args.port}")
        uvicorn.run(
            "src.api:app",
            host=args.host,
            port=args.port,
            reload=True
        )
        
    elif args.mode == "gradio":
        # Run Gradio frontend
        print(f"Starting Gradio frontend on port {args.gradio_port}")
        from src.gradio_frontend import create_interface
        interface = create_interface()
        interface.launch(
            server_name="0.0.0.0",
            server_port=args.gradio_port,
            share=False,
            show_error=True
        )

if __name__ == "__main__":
    main()
