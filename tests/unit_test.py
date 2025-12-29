"""
Unit tests for ECDH key exchange functionality

NOTE: These tests have been migrated to test_encryption_strategies.py
which provides comprehensive testing of the new Strategy pattern architecture.

The tests below are maintained for backward compatibility but now use
the encryption strategy API.
"""

import pytest
import asyncio
from io import BytesIO
from server.protocol import ProtocolHandler
from server.encryption_strategy import ECDHEncryptionStrategy


class TestECDH:
    """Test ECDH key exchange implementation"""

    def test_ecdh_key_generation(self):
        """Test that ECDH strategy generates keys correctly"""
        strategy = ECDHEncryptionStrategy()

        # Check that keys are generated
        assert strategy.private_key is not None
        assert strategy.public_key is not None
        # Cipher should be None until handshake
        assert strategy.cipher is None

    def test_ecdh_public_key_export(self):
        """Test exporting public key as bytes"""
        strategy = ECDHEncryptionStrategy()

        pubkey_bytes = strategy._get_public_key_bytes()

        # X25519 public keys are always 32 bytes
        assert len(pubkey_bytes) == 32
        assert isinstance(pubkey_bytes, bytes)

    @pytest.mark.asyncio
    async def test_ecdh_key_exchange(self):
        """Test ECDH key exchange between two parties"""
        # Simulate server and client
        server_strategy = ECDHEncryptionStrategy()
        client_strategy = ECDHEncryptionStrategy()

        # Exchange public keys
        server_pubkey = server_strategy._get_public_key_bytes()
        client_pubkey = client_strategy._get_public_key_bytes()

        # Both parties derive shared key
        server_strategy._derive_shared_key(client_pubkey)
        client_strategy._derive_shared_key(server_pubkey)

        # Both should now have cipher initialized
        assert server_strategy.cipher is not None
        assert client_strategy.cipher is not None

    def test_ecdh_encryption_decryption(self):
        """Test that messages encrypted with ECDH can be decrypted"""
        # Simulate server and client
        server_strategy = ECDHEncryptionStrategy()
        client_strategy = ECDHEncryptionStrategy()

        # Perform key exchange
        server_pubkey = server_strategy._get_public_key_bytes()
        client_pubkey = client_strategy._get_public_key_bytes()
        server_strategy._derive_shared_key(client_pubkey)
        client_strategy._derive_shared_key(server_pubkey)

        # Create protocol handlers with the strategies
        server_protocol = ProtocolHandler(encryption_strategy=server_strategy)
        client_protocol = ProtocolHandler(encryption_strategy=client_strategy)

        # Test message
        test_message = {
            "type": "echo",
            "message": "ECDH encryption test"
        }

        # Server encrypts message
        encrypted = server_protocol.encode_message(test_message)

        # Extract payload (remove 4-byte length prefix)
        payload = encrypted[4:]

        # Client decrypts message
        decrypted = client_protocol.decode_message(payload)

        # Message should match
        assert decrypted == test_message

    def test_ecdh_bidirectional_communication(self):
        """Test bidirectional encrypted communication"""
        # Simulate server and client
        server_strategy = ECDHEncryptionStrategy()
        client_strategy = ECDHEncryptionStrategy()

        # Perform key exchange
        server_pubkey = server_strategy._get_public_key_bytes()
        client_pubkey = client_strategy._get_public_key_bytes()
        server_strategy._derive_shared_key(client_pubkey)
        client_strategy._derive_shared_key(server_pubkey)

        # Create protocol handlers
        server_protocol = ProtocolHandler(encryption_strategy=server_strategy)
        client_protocol = ProtocolHandler(encryption_strategy=client_strategy)

        # Server to client
        server_msg = {"type": "command", "data": "execute task"}
        encrypted = server_protocol.encode_message(server_msg)
        decrypted = client_protocol.decode_message(encrypted[4:])
        assert decrypted == server_msg

        # Client to server
        client_msg = {"type": "result", "output": "task completed"}
        encrypted = client_protocol.encode_message(client_msg)
        decrypted = server_protocol.decode_message(encrypted[4:])
        assert decrypted == client_msg

    def test_ecdh_different_keys_fail(self):
        """Test that messages encrypted with one keypair cannot be decrypted with another"""
        # Create two independent ECDH sessions
        strategy1 = ECDHEncryptionStrategy()
        strategy2 = ECDHEncryptionStrategy()
        strategy3 = ECDHEncryptionStrategy()
        strategy4 = ECDHEncryptionStrategy()

        # First pair establishes shared key
        strategy1._derive_shared_key(strategy2._get_public_key_bytes())
        strategy2._derive_shared_key(strategy1._get_public_key_bytes())

        # Second pair establishes different shared key
        strategy3._derive_shared_key(strategy4._get_public_key_bytes())
        strategy4._derive_shared_key(strategy3._get_public_key_bytes())

        # Create protocols
        protocol1 = ProtocolHandler(encryption_strategy=strategy1)
        protocol3 = ProtocolHandler(encryption_strategy=strategy3)

        # Encrypt with first pair
        message = {"type": "test", "data": "secret"}
        encrypted = protocol1.encode_message(message)

        # Try to decrypt with second pair
        with pytest.raises(ValueError):
            protocol3.decode_message(encrypted[4:])

    @pytest.mark.asyncio
    async def test_ecdh_full_handshake(self):
        """Test complete ECDH handshake flow"""
        # This test simulates the full handshake as it happens in the real application
        # The actual handshake is tested in test_encryption_strategies.py
        # This is a simplified version for backward compatibility

        server_strategy = ECDHEncryptionStrategy()
        client_strategy = ECDHEncryptionStrategy()

        # Exchange public keys
        server_pubkey = server_strategy._get_public_key_bytes()
        client_pubkey = client_strategy._get_public_key_bytes()

        # Derive shared keys
        server_strategy._derive_shared_key(client_pubkey)
        client_strategy._derive_shared_key(server_pubkey)

        # Verify both have ciphers
        assert server_strategy.cipher is not None
        assert client_strategy.cipher is not None

        # Verify they can communicate
        server_protocol = ProtocolHandler(encryption_strategy=server_strategy)
        client_protocol = ProtocolHandler(encryption_strategy=client_strategy)

        test_msg = {"type": "handshake", "status": "complete"}
        encrypted = server_protocol.encode_message(test_msg)
        decrypted = client_protocol.decode_message(encrypted[4:])

        assert decrypted == test_msg
