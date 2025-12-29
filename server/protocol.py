"""
Protocol module for C2 Server
Handles message framing with length-prefixed protocol and encryption

Protocol Format:
- 4-byte length prefix (big-endian) indicating payload size
- JSON payload (optionally encrypted)

Citation: Length-prefixed framing pattern adapted from Python asyncio documentation
https://docs.python.org/3/library/asyncio-stream.html
"""

import struct
import json
import asyncio
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
import os
import config


class ProtocolHandler:
    """Handles message encoding/decoding with optional encryption"""

    def __init__(self, encryption_key: Optional[bytes] = None):
        """
        Initialize protocol handler

        Args:
            encryption_key: Optional 32-byte key for AES-256-GCM encryption
        """
        self.encryption_enabled = encryption_key is not None
        if self.encryption_enabled:
            # AES-GCM provides authenticated encryption
            # Citation: Cryptography library AESGCM documentation
            # https://cryptography.io/en/latest/hazmat/primitives/aead/
            self.cipher = AESGCM(encryption_key)

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

        # Encrypt if enabled
        if self.encryption_enabled:
            # Generate random nonce (12 bytes recommended for GCM)
            nonce = os.urandom(12)
            # Encrypt and authenticate
            encrypted_data = self.cipher.encrypt(nonce, json_data, None)
            # Prepend nonce to encrypted data
            payload = nonce + encrypted_data
        else:
            payload = json_data

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
        # Decrypt if enabled
        if self.encryption_enabled:
            # Extract nonce (first 12 bytes)
            nonce = data[:12]
            encrypted_data = data[12:]

            try:
                # Decrypt and verify authentication tag
                json_data = self.cipher.decrypt(nonce, encrypted_data, None)
            except InvalidTag:
                raise ValueError("Decryption failed: invalid authentication tag")
        else:
            json_data = data

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
