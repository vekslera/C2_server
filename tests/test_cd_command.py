"""
Tests for cd command functionality
Validates working directory tracking per client
"""

import pytest
import os
import tempfile
from client.c2_client import C2Client


@pytest.mark.asyncio
class TestCdCommand:
    """Test cd command and working directory tracking"""

    async def test_cd_to_valid_directory(self):
        """Test changing to a valid directory"""
        client = C2Client("127.0.0.1", 8888, encryption_key=None)

        # Change to /tmp
        result, success = await client.executor.execute_cd("/tmp")

        assert success is True
        assert client.executor.working_directory == "/tmp"
        assert "Changed directory to /tmp" in result

    async def test_cd_to_nonexistent_directory(self):
        """Test changing to a nonexistent directory"""
        client = C2Client("127.0.0.1", 8888, encryption_key=None)

        result, success = await client.executor.execute_cd("/nonexistent_dir_12345")

        assert success is False
        assert "No such file or directory" in result
        # Working directory should not change
        assert client.executor.working_directory != "/nonexistent_dir_12345"

    async def test_cd_relative_path(self):
        """Test changing to a relative directory"""
        client = C2Client("127.0.0.1", 8888, encryption_key=None)

        # Set initial directory to /tmp
        client.executor.working_directory = "/tmp"

        # Create a temp directory for testing
        with tempfile.TemporaryDirectory(dir="/tmp") as tmpdir:
            dirname = os.path.basename(tmpdir)
            result, success = await client.executor.execute_cd(dirname)

            assert success is True
            assert client.executor.working_directory == tmpdir

    async def test_cd_parent_directory(self):
        """Test changing to parent directory"""
        client = C2Client("127.0.0.1", 8888, encryption_key=None)

        # Start in /tmp/test
        client.executor.working_directory = "/tmp"

        # Go to parent
        result, success = await client.executor.execute_cd("..")

        assert success is True
        assert client.executor.working_directory == "/"

    async def test_cd_home_directory(self):
        """Test changing to home directory with ~"""
        client = C2Client("127.0.0.1", 8888, encryption_key=None)

        result, success = await client.executor.execute_cd("~")

        assert success is True
        assert client.executor.working_directory == os.path.expanduser("~")

    async def test_bash_command_uses_working_directory(self):
        """Test that bash commands execute in the working directory"""
        client = C2Client("127.0.0.1", 8888, encryption_key=None)

        # Change to /tmp
        client.executor.working_directory = "/tmp"

        # Run pwd command
        result, success = await client.executor.execute_bash("pwd")

        assert success is True
        assert "/tmp" in result.strip()

    async def test_multiple_clients_independent_directories(self):
        """Test that different clients maintain separate working directories"""
        client1 = C2Client("127.0.0.1", 8888, encryption_key=None)
        client2 = C2Client("127.0.0.1", 8888, encryption_key=None)

        # Change client1 to /tmp
        await client1.executor.execute_cd("/tmp")

        # Change client2 to /
        await client2.executor.execute_cd("/")

        # Verify they are independent
        assert client1.executor.working_directory == "/tmp"
        assert client2.executor.working_directory == "/"
