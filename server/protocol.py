"""
Protocol module for C2 Server
Handles message framing with length-prefixed protocol and encryption

Protocol Format:
- 4-byte length prefix (big-endian) indicating payload size
- JSON payload (optionally encrypted)

Key Exchange:
- ECDH (Elliptic Curve Diffie-Hellman) for secure key derivation
- X25519 curve for efficient and secure key exchange

Citations:
- Length-prefixed framing: Python asyncio documentation (https://docs.python.org/3/library/asyncio-stream.html)
- ECDH: Cryptography library documentation (https://cryptography.io/en/latest/hazmat/primitives/asymmetric/x25519/)
- HKDF: Cryptography library documentation (https://cryptography.io/en/latest/hazmat/primitives/kdf/hkdf/)
"""

import struct
import json
import asyncio
from typing import Dict, Any, Optional, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.exceptions import InvalidTag
import os
import config


class ProtocolHandler:
    """Handles message encoding/decoding with optional encryption"""

    def __init__(self, encryption_key: Optional[bytes] = None, use_ecdh: bool = False):
        """
        Initialize protocol handler

        Args:
            encryption_key: Optional 32-byte key for AES-256-GCM encryption (PSK mode)
            use_ecdh: If True, use ECDH key exchange instead of PSK
        """
        self.use_ecdh = use_ecdh
        self.encryption_enabled = encryption_key is not None or use_ecdh
        self.cipher = None

        if use_ecdh:
            # Generate ephemeral ECDH key pair
            self.private_key = X25519PrivateKey.generate()
            self.public_key = self.private_key.public_key()
            # Cipher will be initialized after key exchange
        elif encryption_key is not None:
            # AES-GCM provides authenticated encryption
            # Citation: Cryptography library AESGCM documentation
            # https://cryptography.io/en/latest/hazmat/primitives/aead/
            self.cipher = AESGCM(encryption_key)

    def get_public_key_bytes(self) -> bytes:
        """
        Get the public key as bytes for transmission

        Returns:
            32-byte public key
        """
        if not self.use_ecdh:
            raise ValueError("ECDH not enabled")

        return self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

    def derive_shared_key(self, peer_public_key_bytes: bytes) -> None:
        """
        Perform ECDH key exchange and derive AES key

        Args:
            peer_public_key_bytes: Peer's 32-byte public key
        """
        if not self.use_ecdh:
            raise ValueError("ECDH not enabled")

        # Load peer's public key
        peer_public_key = X25519PublicKey.from_public_bytes(peer_public_key_bytes)

        # Perform ECDH to get shared secret
        shared_secret = self.private_key.exchange(peer_public_key)

        # Derive 32-byte AES key using HKDF
        # Citation: HKDF for key derivation
        # https://cryptography.io/en/latest/hazmat/primitives/kdf/hkdf/
        kdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b'c2-server-encryption-key',
        )
        derived_key = kdf.derive(shared_secret)

        # Initialize cipher with derived key
        self.cipher = AESGCM(derived_key)

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
