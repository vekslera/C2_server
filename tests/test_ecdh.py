"""
Unit tests for ECDH key exchange functionality
"""

import pytest
import asyncio
from server.protocol import ProtocolHandler


class TestECDH:
    """Test ECDH key exchange implementation"""

    def test_ecdh_key_generation(self):
        """Test that ECDH protocol handler generates keys correctly"""
        protocol = ProtocolHandler(use_ecdh=True)

        # Check that keys are generated
        assert protocol.private_key is not None
        assert protocol.public_key is not None
        assert protocol.use_ecdh is True
        assert protocol.encryption_enabled is True
        # Cipher should be None until key exchange
        assert protocol.cipher is None

    def test_ecdh_public_key_export(self):
        """Test exporting public key as bytes"""
        protocol = ProtocolHandler(use_ecdh=True)

        pubkey_bytes = protocol.get_public_key_bytes()

        # X25519 public keys are always 32 bytes
        assert len(pubkey_bytes) == 32
        assert isinstance(pubkey_bytes, bytes)

    def test_ecdh_key_exchange(self):
        """Test ECDH key exchange between two parties"""
        # Simulate server and client
        server_protocol = ProtocolHandler(use_ecdh=True)
        client_protocol = ProtocolHandler(use_ecdh=True)

        # Exchange public keys
        server_pubkey = server_protocol.get_public_key_bytes()
        client_pubkey = client_protocol.get_public_key_bytes()

        # Both parties derive shared key
        server_protocol.derive_shared_key(client_pubkey)
        client_protocol.derive_shared_key(server_pubkey)

        # Both should now have cipher initialized
        assert server_protocol.cipher is not None
        assert client_protocol.cipher is not None

    def test_ecdh_encryption_decryption(self):
        """Test that messages encrypted with ECDH can be decrypted"""
        # Simulate server and client
        server_protocol = ProtocolHandler(use_ecdh=True)
        client_protocol = ProtocolHandler(use_ecdh=True)

        # Perform key exchange
        server_pubkey = server_protocol.get_public_key_bytes()
        client_pubkey = client_protocol.get_public_key_bytes()
        server_protocol.derive_shared_key(client_pubkey)
        client_protocol.derive_shared_key(server_pubkey)

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
        server_protocol = ProtocolHandler(use_ecdh=True)
        client_protocol = ProtocolHandler(use_ecdh=True)

        # Perform key exchange
        server_pubkey = server_protocol.get_public_key_bytes()
        client_pubkey = client_protocol.get_public_key_bytes()
        server_protocol.derive_shared_key(client_pubkey)
        client_protocol.derive_shared_key(server_pubkey)

        # Test messages
        client_message = {"type": "command", "data": "test from client"}
        server_message = {"type": "response", "data": "test from server"}

        # Client sends to server
        encrypted_client = client_protocol.encode_message(client_message)
        decrypted_at_server = server_protocol.decode_message(encrypted_client[4:])
        assert decrypted_at_server == client_message

        # Server sends to client
        encrypted_server = server_protocol.encode_message(server_message)
        decrypted_at_client = client_protocol.decode_message(encrypted_server[4:])
        assert decrypted_at_client == server_message

    def test_ecdh_different_keys_fail(self):
        """Test that messages encrypted with different keys cannot be decrypted"""
        # Create three protocol handlers with different keys
        protocol1 = ProtocolHandler(use_ecdh=True)
        protocol2 = ProtocolHandler(use_ecdh=True)
        protocol3 = ProtocolHandler(use_ecdh=True)

        # Exchange keys between 1 and 2
        protocol1.derive_shared_key(protocol2.get_public_key_bytes())
        protocol2.derive_shared_key(protocol1.get_public_key_bytes())

        # Protocol 3 exchanges with itself (different key than 1-2)
        protocol3.derive_shared_key(protocol3.get_public_key_bytes())

        # Message encrypted by protocol1
        test_message = {"type": "test", "data": "secret"}
        encrypted = protocol1.encode_message(test_message)
        payload = encrypted[4:]

        # Protocol2 should decrypt successfully
        decrypted = protocol2.decode_message(payload)
        assert decrypted == test_message

        # Protocol3 should fail to decrypt
        with pytest.raises(ValueError, match="Decryption failed"):
            protocol3.decode_message(payload)

    @pytest.mark.asyncio
    async def test_ecdh_full_handshake(self):
        """Test full ECDH handshake simulation"""
        # This simulates what happens in the actual server/client

        # Create in-memory streams for testing
        server_to_client = asyncio.Queue()
        client_to_server = asyncio.Queue()

        # Server side
        server_protocol = ProtocolHandler(use_ecdh=True)
        server_pubkey = server_protocol.get_public_key_bytes()

        # Client side
        client_protocol = ProtocolHandler(use_ecdh=True)
        client_pubkey = client_protocol.get_public_key_bytes()

        # Simulate handshake
        # 1. Server sends its public key
        await server_to_client.put(server_pubkey)

        # 2. Client receives server's public key
        received_server_pubkey = await server_to_client.get()
        assert len(received_server_pubkey) == 32

        # 3. Client sends its public key
        await client_to_server.put(client_pubkey)

        # 4. Server receives client's public key
        received_client_pubkey = await client_to_server.get()
        assert len(received_client_pubkey) == 32

        # 5. Both derive shared key
        server_protocol.derive_shared_key(received_client_pubkey)
        client_protocol.derive_shared_key(received_server_pubkey)

        # 6. Test encrypted communication
        test_message = {"type": "welcome", "message": "Connected"}

        # Server sends encrypted message
        encrypted = server_protocol.encode_message(test_message)
        await server_to_client.put(encrypted[4:])  # Remove length prefix

        # Client receives and decrypts
        encrypted_payload = await server_to_client.get()
        decrypted = client_protocol.decode_message(encrypted_payload)

        assert decrypted == test_message
