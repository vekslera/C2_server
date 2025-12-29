"""
Tests for protocol module - message framing and encryption
"""

import pytest
import struct
from server.protocol import ProtocolHandler
import config


class TestProtocolHandler:
    """Test protocol encoding/decoding"""

    def test_encode_decode_without_encryption(self):
        """Test message encoding and decoding without encryption"""
        protocol = ProtocolHandler(encryption_key=None)

        message = {"type": "test", "data": "hello world"}
        encoded = protocol.encode_message(message)

        # Check length prefix
        assert len(encoded) > 4
        length = struct.unpack('>I', encoded[:4])[0]
        assert length == len(encoded) - 4

        # Decode
        decoded = protocol.decode_message(encoded[4:])
        assert decoded == message

    def test_encode_decode_with_encryption(self):
        """Test message encoding and decoding with encryption"""
        key = b'0' * 32  # 32-byte key for AES-256
        protocol = ProtocolHandler(encryption_key=key)

        message = {"type": "test", "data": "secret message"}
        encoded = protocol.encode_message(message)

        # Decode with same key
        decoded = protocol.decode_message(encoded[4:])
        assert decoded == message

    def test_encryption_prevents_tampering(self):
        """Test that encrypted messages cannot be decoded with wrong key"""
        key1 = b'1' * 32
        key2 = b'2' * 32

        protocol1 = ProtocolHandler(encryption_key=key1)
        protocol2 = ProtocolHandler(encryption_key=key2)

        message = {"type": "test", "data": "secret"}
        encoded = protocol1.encode_message(message)

        # Try to decode with wrong key
        with pytest.raises(ValueError):
            protocol2.decode_message(encoded[4:])

    def test_large_message(self):
        """Test encoding/decoding large messages"""
        protocol = ProtocolHandler(encryption_key=None)

        # Create large message
        large_data = "x" * 10000
        message = {"type": "test", "data": large_data}

        encoded = protocol.encode_message(message)
        decoded = protocol.decode_message(encoded[4:])

        assert decoded == message

    def test_message_length_validation(self):
        """Test that oversized messages are rejected"""
        protocol = ProtocolHandler(encryption_key=None)

        # Create message exceeding MAX_MESSAGE_SIZE
        oversized_data = "x" * (config.MAX_MESSAGE_SIZE + 1000)
        message = {"type": "test", "data": oversized_data}

        with pytest.raises(ValueError, match="Message too large"):
            protocol.encode_message(message)
