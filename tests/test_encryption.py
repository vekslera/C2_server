"""
Tests for Step 2 - Encryption
Validates AES-256-GCM encryption between server and client
"""

import pytest
import config
from server.protocol import ProtocolHandler
from server.encryption_strategy import PSKEncryptionStrategy


class TestEncryption:
    """Test encryption functionality"""

    def test_psk_length(self):
        """Verify PSK is exactly 32 bytes for AES-256"""
        assert len(config.ENCRYPTION_PSK) == 32

    def test_encrypted_message_differs_from_plaintext(self):
        """Encrypted message should not contain plaintext"""
        protocol = ProtocolHandler(encryption_strategy=PSKEncryptionStrategy(config.ENCRYPTION_PSK))

        message = {"type": "test", "secret": "sensitive_data"}
        encoded = protocol.encode_message(message)

        # Check that plaintext is not in encoded message
        assert b"sensitive_data" not in encoded
        assert b"secret" not in encoded

    def test_encrypted_round_trip(self):
        """Test full encryption and decryption cycle"""
        protocol = ProtocolHandler(encryption_strategy=PSKEncryptionStrategy(config.ENCRYPTION_PSK))

        original = {
            "type": "command",
            "command_id": "test-123",
            "command": "echo 'secret message'"
        }

        # Encode
        encoded = protocol.encode_message(original)

        # Decode
        decoded = protocol.decode_message(encoded[4:])

        assert decoded == original

    def test_different_keys_cannot_decrypt(self):
        """Messages encrypted with one key cannot be decrypted with another"""
        key1 = b'k' * 32
        key2 = b'x' * 32

        protocol1 = ProtocolHandler(encryption_strategy=PSKEncryptionStrategy(key1))
        protocol2 = ProtocolHandler(encryption_strategy=PSKEncryptionStrategy(key2))

        message = {"type": "test", "data": "secret"}
        encoded = protocol1.encode_message(message)

        # Attempt to decode with wrong key
        with pytest.raises(ValueError, match="Decryption failed"):
            protocol2.decode_message(encoded[4:])

    def test_nonce_is_random(self):
        """Each encrypted message should have a different nonce"""
        protocol = ProtocolHandler(encryption_strategy=PSKEncryptionStrategy(config.ENCRYPTION_PSK))

        message = {"type": "test", "data": "same"}

        encoded1 = protocol.encode_message(message)
        encoded2 = protocol.encode_message(message)

        # Same message should produce different ciphertext due to random nonce
        assert encoded1 != encoded2
