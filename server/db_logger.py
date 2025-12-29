"""
Database Logger for C2 Server
Logs events, commands, and results to PostgreSQL database

Citation: psycopg2 async usage
https://www.psycopg.org/docs/usage.html
"""

import asyncio
import psycopg2
from psycopg2 import pool
import logging
from typing import Optional
import config

logger = logging.getLogger(__name__)


class DatabaseLogger:
    """Handles database logging operations"""

    def __init__(self):
        """Initialize database logger"""
        self.connection_pool: Optional[pool.SimpleConnectionPool] = None

    def connect(self) -> None:
        """
        Create connection pool to PostgreSQL database

        Citation: psycopg2 connection pooling
        https://www.psycopg.org/docs/pool.html
        """
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                1,  # Min connections
                10,  # Max connections
                host=config.DB_HOST,
                port=config.DB_PORT,
                database=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD
            )
            logger.info("Database connection pool created successfully")
        except Exception as e:
            logger.error(f"Failed to create database connection pool: {e}")
            self.connection_pool = None

    async def log_event(self, event_type: str, client_id: str, details: str = None) -> None:
        """
        Log an event to the database

        Args:
            event_type: Type of event (e.g., "client_connected")
            client_id: Client identifier
            details: Additional details about the event
        """
        if not self.connection_pool:
            logger.warning("Database not connected, skipping event log")
            return

        # Run blocking DB operation in executor
        await asyncio.get_event_loop().run_in_executor(
            None,
            self._log_event_sync,
            event_type,
            client_id,
            details
        )

    def _log_event_sync(self, event_type: str, client_id: str, details: str = None) -> None:
        """Synchronous event logging"""
        conn = None
        try:
            conn = self.connection_pool.getconn()
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO events (event_type, client_id, details) VALUES (%s, %s, %s)",
                (event_type, client_id, str(details) if details else None)
            )

            conn.commit()
            cursor.close()
            logger.debug(f"Logged event: {event_type} for client {client_id}")
        except Exception as e:
            logger.error(f"Failed to log event: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                self.connection_pool.putconn(conn)

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
        if not self.connection_pool:
            return

        await asyncio.get_event_loop().run_in_executor(
            None,
            self._log_command_sync,
            client_id,
            command_id,
            command_type,
            command
        )

    def _log_command_sync(self, client_id: str, command_id: str,
                         command_type: str, command: str) -> None:
        """Synchronous command logging"""
        conn = None
        try:
            conn = self.connection_pool.getconn()
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO commands (client_id, command_id, command_type, command) VALUES (%s, %s, %s, %s)",
                (client_id, command_id, command_type, command)
            )

            conn.commit()
            cursor.close()
        except Exception as e:
            logger.error(f"Failed to log command: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                self.connection_pool.putconn(conn)

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
        if not self.connection_pool:
            return

        await asyncio.get_event_loop().run_in_executor(
            None,
            self._log_result_sync,
            client_id,
            command_id,
            result,
            success
        )

    def _log_result_sync(self, client_id: str, command_id: str,
                        result: str, success: bool) -> None:
        """Synchronous result logging"""
        conn = None
        try:
            conn = self.connection_pool.getconn()
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO results (client_id, command_id, result, success) VALUES (%s, %s, %s, %s)",
                (client_id, command_id, result, success)
            )

            conn.commit()
            cursor.close()
        except Exception as e:
            logger.error(f"Failed to log result: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                self.connection_pool.putconn(conn)

    def close(self) -> None:
        """Close all database connections"""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("Database connections closed")
