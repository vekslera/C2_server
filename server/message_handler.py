"""
Message Handler Module
Processes different message types from clients
Separated for Single Responsibility Principle
"""

import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MessageHandler:
    """Handles incoming messages from C2 clients"""

    def __init__(self, db_logger=None):
        """
        Initialize message handler

        Args:
            db_logger: Optional database logger instance
        """
        self.db_logger = db_logger

    async def handle_heartbeat(self, client, protocol, message: Dict) -> None:
        """
        Handle heartbeat message

        Args:
            client: ClientConnection instance
            protocol: ProtocolHandler instance
            message: Message dictionary
        """
        client.update_heartbeat()
        logger.debug(f"Heartbeat from {client.client_id}")

        # Send acknowledgment
        await protocol.write_message(client.writer, {
            "type": "heartbeat_ack"
        })

    async def handle_command_result(self, client, message: Dict, cli=None) -> None:
        """
        Handle command execution result

        Args:
            client: ClientConnection instance
            message: Message dictionary
            cli: Optional CLI instance for prompt refresh
        """
        command_id = message.get("command_id")
        result = message.get("result")
        success = message.get("success", True)

        logger.info(f"Command {command_id} result from {client.client_id}: success={success}")

        # Log to database if available
        if self.db_logger:
            await self.db_logger.log_command_result(
                client.client_id, command_id, result, success
            )

        # Print result to console
        print(f"\n[Result from {client.client_id}]")
        print(f"Command ID: {command_id}")
        print(f"Success: {success}")
        print(f"Output:\n{result}")
        print()

        # Reprint CLI prompt if available
        if cli:
            cli.reprint_prompt()

    async def process_message(self, client, protocol, message: Dict, cli=None) -> bool:
        """
        Route message to appropriate handler

        Args:
            client: ClientConnection instance
            protocol: ProtocolHandler instance
            message: Message dictionary
            cli: Optional CLI instance

        Returns:
            True if message was handled, False if unknown type
        """
        msg_type = message.get("type")
        logger.debug(f"Received from {client.client_id}: {msg_type}")

        if msg_type == "heartbeat":
            await self.handle_heartbeat(client, protocol, message)
            return True

        elif msg_type == "command_result":
            await self.handle_command_result(client, message, cli)
            return True

        else:
            logger.warning(f"Unknown message type from {client.client_id}: {msg_type}")
            return False
