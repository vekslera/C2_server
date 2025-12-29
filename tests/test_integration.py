"""
Integration tests for C2 Server and Client
Tests end-to-end functionality
"""

import pytest
import pytest_asyncio
import asyncio
from server.c2_server import C2Server
from client.c2_client import C2Client
import config


@pytest.mark.asyncio
class TestC2Integration:
    """Integration tests for server-client communication"""

    @pytest_asyncio.fixture
    async def server(self):
        """Fixture to start a test server"""
        server = C2Server(
            host="127.0.0.1",
            port=9999,  # Use different port for testing
            encryption_strategy=None
        )

        # Start server in background
        server_task = asyncio.create_task(server.start())
        await asyncio.sleep(0.5)  # Give server time to start

        yield server

        # Cleanup
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

    async def test_client_connection(self, server):
        """Test that client can connect to server"""
        client = C2Client(
            server_host="127.0.0.1",
            server_port=9999,
            encryption_strategy=None
        )

        # Connect
        success = await client.connect()
        assert success
        assert client.client_id is not None

        # Verify server sees the client
        await asyncio.sleep(0.1)
        clients = server.list_clients()
        assert len(clients) == 1
        assert clients[0]["client_id"] == client.client_id

        # Cleanup
        await client.disconnect()

    async def test_multiple_clients(self, server):
        """Test server handling multiple clients"""
        clients = []

        # Connect 3 clients
        for i in range(3):
            client = C2Client(
                server_host="127.0.0.1",
                server_port=9999,
                encryption_strategy=None
            )
            await client.connect()
            clients.append(client)

        await asyncio.sleep(0.2)

        # Verify all connected
        server_clients = server.list_clients()
        assert len(server_clients) == 3

        # Cleanup
        for client in clients:
            await client.disconnect()

    async def test_echo_command(self, server):
        """Test echo command execution"""
        client = C2Client(
            server_host="127.0.0.1",
            server_port=9999,
            encryption_strategy=None
        )

        await client.connect()

        # Start client message receiver in background
        receive_task = asyncio.create_task(client.receive_messages())
        processor_task = asyncio.create_task(client.command_processor())

        await asyncio.sleep(0.1)

        # Send echo command from server
        success = await server.send_command(
            client.client_id,
            "Test Message",
            command_type="echo"
        )

        assert success

        # Wait for processing
        await asyncio.sleep(0.3)

        # Cleanup
        client.running = False
        receive_task.cancel()
        processor_task.cancel()
        await client.disconnect()

    async def test_heartbeat_mechanism(self, server):
        """Test heartbeat functionality"""
        client = C2Client(
            server_host="127.0.0.1",
            server_port=9999,
            encryption_strategy=None
        )

        await client.connect()

        # Start client tasks
        receive_task = asyncio.create_task(client.receive_messages())
        heartbeat_task = asyncio.create_task(client.send_heartbeat())

        await asyncio.sleep(0.2)

        # Verify client is alive
        clients = server.list_clients()
        assert len(clients) == 1
        assert clients[0]["is_alive"] is True

        # Cleanup
        client.running = False
        receive_task.cancel()
        heartbeat_task.cancel()
        await client.disconnect()


@pytest.mark.asyncio
async def test_database_logging():
    """Test database logging functionality (Step 3)"""
    from server.db_logger import DatabaseLogger
    import psycopg2

    # Create and connect database logger
    db_logger = DatabaseLogger()
    db_logger.connect()

    try:
        # Log an event
        await db_logger.log_event("test_event", "test_client_123", "test details")

        # Verify it was logged
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        cursor = conn.cursor()
        cursor.execute("SELECT event_type, client_id FROM events WHERE client_id = 'test_client_123'")
        result = cursor.fetchone()

        assert result is not None
        assert result[0] == "test_event"
        assert result[1] == "test_client_123"

        cursor.close()
        conn.close()

    finally:
        db_logger.close()


def test_config_values():
    """Test that configuration values are set correctly"""
    assert config.SERVER_PORT > 0
    assert config.MESSAGE_LENGTH_PREFIX_SIZE == 4
    assert len(config.ENCRYPTION_PSK) == 32
    assert config.HEARTBEAT_INTERVAL > 0
