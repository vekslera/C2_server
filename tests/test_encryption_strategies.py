"""
Unit tests for encryption strategies (Strategy pattern refactoring)
"""

import pytest
import asyncio
from server.encryption_strategy import ECDHEncryptionStrategy, PSKEncryptionStrategy, NoEncryptionStrategy
from server.protocol import ProtocolHandler


class TestEncryptionStrategies:
    """Test encryption strategies"""

    def test_no_encryption_strategy(self):
        """Test no encryption strategy"""
        strategy = NoEncryptionStrategy()

        plaintext = b"Hello, World!"
        encrypted = strategy.encrypt(plaintext)
        decrypted = strategy.decrypt(encrypted)

        assert encrypted == plaintext
        assert decrypted == plaintext
        assert not strategy.is_encryption_enabled()

    def test_psk_encryption_strategy(self):
        """Test PSK encryption strategy"""
        psk = b"0" * 32  # 32-byte key
        strategy = PSKEncryptionStrategy(psk)

        plaintext = b"Secret message"
        encrypted = strategy.encrypt(plaintext)
        decrypted = strategy.decrypt(encrypted)

        assert encrypted != plaintext  # Should be encrypted
        assert len(encrypted) > len(plaintext)  # Includes nonce
        assert decrypted == plaintext
        assert strategy.is_encryption_enabled()

    def test_psk_invalid_key_size(self):
        """Test PSK with invalid key size"""
        with pytest.raises(ValueError, match="PSK must be 32 bytes"):
            PSKEncryptionStrategy(b"short_key")

    def test_ecdh_key_generation(self):
        """Test ECDH key generation"""
        strategy = ECDHEncryptionStrategy()

        assert strategy.private_key is not None
        assert strategy.public_key is not None
        assert strategy.cipher is None  # Not initialized until handshake
        assert strategy.is_encryption_enabled()

    def test_ecdh_public_key_export(self):
        """Test ECDH public key export"""
        strategy = ECDHEncryptionStrategy()
        pubkey_bytes = strategy._get_public_key_bytes()

        assert len(pubkey_bytes) == 32
        assert isinstance(pubkey_bytes, bytes)

    @pytest.mark.asyncio
    async def test_ecdh_handshake(self):
        """Test ECDH handshake simulation"""
        # Create in-memory streams
        server_to_client = asyncio.Queue()
        client_to_server = asyncio.Queue()

        # Mock stream readers/writers
        class MockWriter:
            def __init__(self, queue):
                self.queue = queue

            def write(self, data):
                asyncio.create_task(self.queue.put(data))

            async def drain(self):
                pass

        class MockReader:
            def __init__(self, queue):
                self.queue = queue

            async def read(self, n):
                return await self.queue.get()

        # Server and client strategies
        server_strategy = ECDHEncryptionStrategy()
        client_strategy = ECDHEncryptionStrategy()

        server_writer = MockWriter(server_to_client)
        server_reader = MockReader(client_to_server)
        client_writer = MockWriter(client_to_server)
        client_reader = MockReader(server_to_client)

        # Perform handshake
        await asyncio.gather(
            server_strategy.perform_handshake(server_reader, server_writer, is_server=True),
            client_strategy.perform_handshake(client_reader, client_writer, is_server=False)
        )

        # Both should have cipher initialized
        assert server_strategy.cipher is not None
        assert client_strategy.cipher is not None

        # Test encryption/decryption
        plaintext = b"Test message"
        encrypted = server_strategy.encrypt(plaintext)
        decrypted = client_strategy.decrypt(encrypted)
        assert decrypted == plaintext

    def test_ecdh_encryption_before_handshake(self):
        """Test that encryption fails before handshake"""
        strategy = ECDHEncryptionStrategy()

        with pytest.raises(RuntimeError, match="Encryption not initialized"):
            strategy.encrypt(b"test")

    def test_ecdh_decryption_before_handshake(self):
        """Test that decryption fails before handshake"""
        strategy = ECDHEncryptionStrategy()

        with pytest.raises(RuntimeError, match="Encryption not initialized"):
            strategy.decrypt(b"test")

    def test_ecdh_different_keys_fail(self):
        """Test that messages encrypted with different keys cannot be decrypted"""
        # Create two separate ECDH pairs
        strategy1 = ECDHEncryptionStrategy()
        strategy2 = ECDHEncryptionStrategy()

        # Exchange keys between strategy1 and itself
        strategy1._derive_shared_key(strategy1._get_public_key_bytes())

        # Exchange keys between strategy2 and itself
        strategy2._derive_shared_key(strategy2._get_public_key_bytes())

        # Encrypt with strategy1
        plaintext = b"Secret"
        encrypted = strategy1.encrypt(plaintext)

        # Strategy2 should fail to decrypt
        with pytest.raises(ValueError, match="Decryption failed"):
            strategy2.decrypt(encrypted)


class TestProtocolHandlerWithStrategies:
    """Test protocol handler with different encryption strategies"""

    def test_protocol_with_no_encryption(self):
        """Test protocol handler with no encryption"""
        protocol = ProtocolHandler()

        message = {"type": "test", "data": "hello"}
        encoded = protocol.encode_message(message)
        decoded = protocol.decode_message(encoded[4:])  # Skip length prefix

        assert decoded == message

    def test_protocol_with_psk(self):
        """Test protocol handler with PSK encryption"""
        psk = b"0" * 32
        strategy = PSKEncryptionStrategy(psk)
        protocol = ProtocolHandler(strategy)

        message = {"type": "test", "data": "secret"}
        encoded = protocol.encode_message(message)
        decoded = protocol.decode_message(encoded[4:])  # Skip length prefix

        assert decoded == message

    def test_protocol_with_ecdh(self):
        """Test protocol handler with ECDH encryption"""
        # Create two protocol handlers with ECDH
        server_strategy = ECDHEncryptionStrategy()
        client_strategy = ECDHEncryptionStrategy()

        server_protocol = ProtocolHandler(server_strategy)
        client_protocol = ProtocolHandler(client_strategy)

        # Perform key exchange
        server_pubkey = server_strategy._get_public_key_bytes()
        client_pubkey = client_strategy._get_public_key_bytes()

        server_strategy._derive_shared_key(client_pubkey)
        client_strategy._derive_shared_key(server_pubkey)

        # Test bidirectional communication
        message1 = {"type": "command", "data": "from_server"}
        encoded1 = server_protocol.encode_message(message1)
        decoded1 = client_protocol.decode_message(encoded1[4:])
        assert decoded1 == message1

        message2 = {"type": "response", "data": "from_client"}
        encoded2 = client_protocol.encode_message(message2)
        decoded2 = server_protocol.decode_message(encoded2[4:])
        assert decoded2 == message2
