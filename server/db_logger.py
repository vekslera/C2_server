"""
Database Logger for C2 Server
Logs events, commands, and results to database

DEPRECATED: This module is maintained for backward compatibility.
New code should use server.database.DatabaseInterface directly.

Design: Adapter pattern - wraps DatabaseInterface with legacy API
"""

import logging
from typing import Optional
from server.database import DatabaseInterface
import config

logger = logging.getLogger(__name__)


class DatabaseLogger:
    """
    Handles database logging operations

    Legacy wrapper around DatabaseInterface for backward compatibility
    """

    def __init__(self, database: Optional[DatabaseInterface] = None):
        """
        Initialize database logger

        Args:
            database: Database interface implementation (will be created if None)
        """
        self.database = database

    def connect(self) -> None:
        """Create database connection"""
        if self.database is None:
            # Lazy initialization with PostgreSQL
            from server.database import PostgreSQLDatabase

            self.database = PostgreSQLDatabase(
                host=config.DB_HOST,
                port=config.DB_PORT,
                database=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                min_connections=config.DB_POOL_MIN_CONNECTIONS,
                max_connections=config.DB_POOL_MAX_CONNECTIONS
            )

        self.database.connect()

    async def log_event(self, event_type: str, client_id: str, details: str = None) -> None:
        """
        Log an event to the database

        Args:
            event_type: Type of event (e.g., "client_connected")
            client_id: Client identifier
            details: Additional details about the event
        """
        if self.database:
            await self.database.log_event(event_type, client_id, details)

    async def log_command_sent(self, client_id: str, command_id: str,
                               command_type: str, command: str) -> None:
        """
        Log a command sent to a client

        Args:
            client_id: Client identifier
            command_id: Unique command identifier
            command_type: Type of command
            command: Command text
        """
        if self.database:
            await self.database.log_command(client_id, command_id, command_type, command)

    async def log_command_result(self, client_id: str, command_id: str,
                                 result: str, success: bool) -> None:
        """
        Log a command execution result

        Args:
            client_id: Client identifier
            command_id: Unique command identifier
            result: Command execution result
            success: Whether command succeeded
        """
        if self.database:
            await self.database.log_result(client_id, command_id, result, success)

    def close(self) -> None:
        """Close all database connections"""
        if self.database:
            self.database.close()
