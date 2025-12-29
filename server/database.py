"""
Database Interface for C2 Server
Provides unified database operations using Repository pattern

Design Patterns:
- Repository Pattern: Abstracts data access logic
- Dependency Inversion: Depend on abstractions, not concrete implementations
- Single Responsibility: One module for all database operations

Citations:
- psycopg2 connection pooling: https://www.psycopg.org/docs/pool.html
- Repository Pattern: Martin Fowler's Patterns of Enterprise Application Architecture
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from abc import ABC, abstractmethod

# Type checking imports - only used by IDE/linters, not at runtime
if TYPE_CHECKING:
    try:
        import psycopg2  # type: ignore[import-not-found]
        from psycopg2 import pool  # type: ignore[import-not-found]
    except ImportError:
        pass  # psycopg2 is optional

logger = logging.getLogger(__name__)


class DatabaseInterface(ABC):
    """Abstract interface for database operations"""

    @abstractmethod
    def connect(self) -> None:
        """Establish database connection"""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close database connections"""
        pass

    @abstractmethod
    async def log_event(self, event_type: str, client_id: str, details: Optional[str] = None) -> None:
        """Log an event"""
        pass

    @abstractmethod
    async def log_command(self, client_id: str, command_id: str, command_type: str, command: str) -> None:
        """Log a command"""
        pass

    @abstractmethod
    async def log_result(self, client_id: str, command_id: str, result: str, success: bool) -> None:
        """Log a command result"""
        pass

    @abstractmethod
    async def get_recent_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent events"""
        pass

    @abstractmethod
    async def get_recent_commands(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent commands"""
        pass

    @abstractmethod
    async def get_recent_results(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent results"""
        pass


class PostgreSQLDatabase(DatabaseInterface):
    """PostgreSQL implementation of database interface"""

    def __init__(self, host: str, port: int, database: str, user: str, password: str,
                 min_connections: int = 1, max_connections: int = 5):
        """
        Initialize PostgreSQL database

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
            min_connections: Minimum connections in pool
            max_connections: Maximum connections in pool
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.connection_pool: Optional[Any] = None  # psycopg2.pool.SimpleConnectionPool

    def connect(self) -> None:
        """Create connection pool to PostgreSQL database"""
        try:
            # Lazy import to avoid dependency issues
            import psycopg2
            from psycopg2 import pool

            self.connection_pool = pool.SimpleConnectionPool(
                self.min_connections,
                self.max_connections,
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            logger.info("Database connection pool created successfully")
        except ImportError:
            logger.error("psycopg2 not installed. Install with: pip install psycopg2-binary")
            self.connection_pool = None
        except Exception as e:
            logger.error(f"Failed to create database connection pool: {e}")
            self.connection_pool = None

    def close(self) -> None:
        """Close all database connections"""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("Database connections closed")

    async def log_event(self, event_type: str, client_id: str, details: Optional[str] = None) -> None:
        """Log an event to the database"""
        if not self.connection_pool:
            logger.warning("Database not connected, skipping event log")
            return

        await asyncio.get_event_loop().run_in_executor(
            None,
            self._log_event_sync,
            event_type,
            client_id,
            details
        )

    def _log_event_sync(self, event_type: str, client_id: str, details: Optional[str]) -> None:
        """Synchronous event logging"""
        if not self.connection_pool:
            return

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
            if conn and self.connection_pool:
                self.connection_pool.putconn(conn)

    async def log_command(self, client_id: str, command_id: str, command_type: str, command: str) -> None:
        """Log a command sent to a client"""
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

    def _log_command_sync(self, client_id: str, command_id: str, command_type: str, command: str) -> None:
        """Synchronous command logging"""
        if not self.connection_pool:
            return

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
            if conn and self.connection_pool:
                self.connection_pool.putconn(conn)

    async def log_result(self, client_id: str, command_id: str, result: str, success: bool) -> None:
        """Log a command execution result"""
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

    def _log_result_sync(self, client_id: str, command_id: str, result: str, success: bool) -> None:
        """Synchronous result logging"""
        if not self.connection_pool:
            return

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
            if conn and self.connection_pool:
                self.connection_pool.putconn(conn)

    async def get_recent_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent events from database"""
        if not self.connection_pool:
            return []

        return await asyncio.get_event_loop().run_in_executor(
            None,
            self._get_recent_events_sync,
            limit
        )

    def _get_recent_events_sync(self, limit: int) -> List[Dict[str, Any]]:
        """Synchronous event retrieval"""
        if not self.connection_pool:
            return []

        conn = None
        try:
            conn = self.connection_pool.getconn()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT timestamp, event_type, client_id, details FROM events ORDER BY timestamp DESC LIMIT %s",
                (limit,)
            )

            events = []
            for row in cursor.fetchall():
                events.append({
                    "timestamp": row[0],
                    "event_type": row[1],
                    "client_id": row[2],
                    "details": row[3]
                })

            cursor.close()
            return events
        except Exception as e:
            logger.error(f"Failed to get events: {e}")
            return []
        finally:
            if conn and self.connection_pool:
                self.connection_pool.putconn(conn)

    async def get_recent_commands(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent commands from database"""
        if not self.connection_pool:
            return []

        return await asyncio.get_event_loop().run_in_executor(
            None,
            self._get_recent_commands_sync,
            limit
        )

    def _get_recent_commands_sync(self, limit: int) -> List[Dict[str, Any]]:
        """Synchronous command retrieval"""
        if not self.connection_pool:
            return []

        conn = None
        try:
            conn = self.connection_pool.getconn()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT timestamp, client_id, command_type, command FROM commands ORDER BY timestamp DESC LIMIT %s",
                (limit,)
            )

            commands = []
            for row in cursor.fetchall():
                commands.append({
                    "timestamp": row[0],
                    "client_id": row[1],
                    "command_type": row[2],
                    "command": row[3]
                })

            cursor.close()
            return commands
        except Exception as e:
            logger.error(f"Failed to get commands: {e}")
            return []
        finally:
            if conn and self.connection_pool:
                self.connection_pool.putconn(conn)

    async def get_recent_results(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent results from database"""
        if not self.connection_pool:
            return []

        return await asyncio.get_event_loop().run_in_executor(
            None,
            self._get_recent_results_sync,
            limit
        )

    def _get_recent_results_sync(self, limit: int) -> List[Dict[str, Any]]:
        """Synchronous result retrieval"""
        if not self.connection_pool:
            return []

        conn = None
        try:
            conn = self.connection_pool.getconn()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT timestamp, client_id, success, result FROM results ORDER BY timestamp DESC LIMIT %s",
                (limit,)
            )

            results = []
            for row in cursor.fetchall():
                results.append({
                    "timestamp": row[0],
                    "client_id": row[1],
                    "success": row[2],
                    "result": row[3]
                })

            cursor.close()
            return results
        except Exception as e:
            logger.error(f"Failed to get results: {e}")
            return []
        finally:
            if conn and self.connection_pool:
                self.connection_pool.putconn(conn)


class NullDatabase(DatabaseInterface):
    """Null object pattern - no-op database for when DB is not needed"""

    def connect(self) -> None:
        pass

    def close(self) -> None:
        pass

    async def log_event(self, event_type: str, client_id: str, details: Optional[str] = None) -> None:
        pass

    async def log_command(self, client_id: str, command_id: str, command_type: str, command: str) -> None:
        pass

    async def log_result(self, client_id: str, command_id: str, result: str, success: bool) -> None:
        pass

    async def get_recent_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        return []

    async def get_recent_commands(self, limit: int = 10) -> List[Dict[str, Any]]:
        return []

    async def get_recent_results(self, limit: int = 10) -> List[Dict[str, Any]]:
        return []
