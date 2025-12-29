"""
Protocol module for C2 Server
Handles message framing with length-prefixed protocol and encryption

Protocol Format:
- 4-byte length prefix (big-endian) indicating payload size
- JSON payload (optionally encrypted based on encryption strategy)

Design:
- Uses Strategy pattern for encryption (SOLID principles)
- Decouples encryption implementation from protocol handling

Citations:
- Length-prefixed framing: Python asyncio documentation (https://docs.python.org/3/library/asyncio-stream.html)
"""

import struct
import json
import asyncio
from typing import Dict, Any, Optional
from server.encryption_strategy import EncryptionStrategy, NoEncryptionStrategy
import config


class ProtocolHandler:
    """Handles message encoding/decoding with pluggable encryption strategy"""

    def __init__(self, encryption_strategy: Optional[EncryptionStrategy] = None):
        """
        Initialize protocol handler

        Args:
            encryption_strategy: Strategy for encryption (None = no encryption)
        """
        self.encryption_strategy = encryption_strategy or NoEncryptionStrategy()

    async def perform_handshake(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        is_server: bool
    ) -> None:
        """
        Perform encryption handshake if needed

        Args:
            reader: Stream reader for receiving data
            writer: Stream writer for sending data
            is_server: True if this is the server side, False if client
        """
        await self.encryption_strategy.perform_handshake(reader, writer, is_server)

    def encode_message(self, message: Dict[str, Any]) -> bytes:
        """
        Encode a message dictionary into length-prefixed bytes

        Args:
            message: Dictionary to encode

        Returns:
            Length-prefixed encoded message
        """
        # Convert to JSON
        json_data = json.dumps(message).encode('utf-8')

        # Encrypt using strategy
        payload = self.encryption_strategy.encrypt(json_data)

        # Check max message size
        if len(payload) > config.MAX_MESSAGE_SIZE:
            raise ValueError(f"Message too large: {len(payload)} bytes")

        # Prepend 4-byte length header (big-endian)
        length_prefix = struct.pack('>I', len(payload))
        return length_prefix + payload

    def decode_message(self, data: bytes) -> Dict[str, Any]:
        """
        Decode length-prefixed bytes into a message dictionary

        Args:
            data: Raw bytes (without length prefix)

        Returns:
            Decoded message dictionary
        """
        # Decrypt using strategy
        json_data = self.encryption_strategy.decrypt(data)

        # Parse JSON
        try:
            message = json.loads(json_data.decode('utf-8'))
            return message
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")

    async def read_message(self, reader: asyncio.StreamReader) -> Optional[Dict[str, Any]]:
        """
        Read a length-prefixed message from a stream reader

        Args:
            reader: asyncio StreamReader

        Returns:
            Decoded message or None if connection closed
        """
        # Read 4-byte length prefix
        length_data = await reader.read(config.MESSAGE_LENGTH_PREFIX_SIZE)
        if not length_data or len(length_data) < config.MESSAGE_LENGTH_PREFIX_SIZE:
            return None

        # Unpack length
        message_length = struct.unpack('>I', length_data)[0]

        # Validate length
        if message_length > config.MAX_MESSAGE_SIZE:
            raise ValueError(f"Message too large: {message_length} bytes")

        # Read message payload
        payload = await reader.read(message_length)
        if len(payload) < message_length:
            raise ValueError("Incomplete message received")

        # Decode message
        return self.decode_message(payload)

    async def write_message(self, writer: asyncio.StreamWriter, message: Dict[str, Any]) -> None:
        """
        Write a length-prefixed message to a stream writer

        Args:
            writer: asyncio StreamWriter
            message: Message dictionary to send
        """
        encoded = self.encode_message(message)
        writer.write(encoded)
        await writer.drain()
