"""
Main entry point for C2 Server
Starts the server and CLI interface
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.c2_server import C2Server
from server.cli import C2CLI
import config


async def main():
    """Main entry point"""
    print("=" * 60)
    print("C2 Server - Command & Control Server")
    print("=" * 60)

    # Initialize server (without encryption for Step 1)
    server = C2Server(
        config.SERVER_HOST,
        config.SERVER_PORT,
        encryption_key=None  # Will be enabled in Step 2
    )

    # Start server in background
    server_task = asyncio.create_task(server.start())

    # Give server time to start
    await asyncio.sleep(1)

    # Run CLI
    cli = C2CLI(server)
    await cli.run()

    # Cleanup
    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        pass

    print("Server shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested...")
