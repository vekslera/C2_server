"""
Encryption strategies for C2 Server
Uses Strategy pattern to decouple encryption implementation from protocol handling

Citations:
- Strategy Pattern: Gang of Four Design Patterns
- SOLID Principles: Open/Closed Principle, Dependency Inversion Principle
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.exceptions import InvalidTag
import os
import asyncio


class EncryptionStrategy(ABC):
    """Abstract base class for encryption strategies"""

    @abstractmethod
    async def perform_handshake(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        is_server: bool
    ) -> None:
        """
        Perform any necessary handshake for key exchange

        Args:
            reader: Stream reader for receiving data
            writer: Stream writer for sending data
            is_server: True if this is the server side, False if client
        """
        pass

    @abstractmethod
    def encrypt(self, plaintext: bytes) -> bytes:
        """
        Encrypt plaintext data

        Args:
            plaintext: Data to encrypt

        Returns:
            Encrypted data (including nonce if needed)
        """
        pass

    @abstractmethod
    def decrypt(self, ciphertext: bytes) -> bytes:
        """
        Decrypt ciphertext data

        Args:
            ciphertext: Data to decrypt (including nonce if needed)

        Returns:
            Decrypted plaintext

        Raises:
            ValueError: If decryption fails
        """
        pass

    @abstractmethod
    def is_encryption_enabled(self) -> bool:
        """Returns True if encryption is enabled"""
        pass


class NoEncryptionStrategy(EncryptionStrategy):
    """Strategy for no encryption (plaintext communication)"""

    async def perform_handshake(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        is_server: bool
    ) -> None:
        """No handshake needed for plaintext"""
        pass

    def encrypt(self, plaintext: bytes) -> bytes:
        """Return plaintext as-is"""
        return plaintext

    def decrypt(self, ciphertext: bytes) -> bytes:
        """Return ciphertext as-is"""
        return ciphertext

    def is_encryption_enabled(self) -> bool:
        return False


class PSKEncryptionStrategy(EncryptionStrategy):
    """Pre-Shared Key encryption strategy using AES-256-GCM"""

    def __init__(self, psk: bytes):
        """
        Initialize PSK encryption strategy

        Args:
            psk: 32-byte pre-shared key for AES-256-GCM
        """
        if len(psk) != 32:
            raise ValueError("PSK must be 32 bytes for AES-256")
        self.cipher = AESGCM(psk)

    async def perform_handshake(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        is_server: bool
    ) -> None:
        """No handshake needed for PSK - key is pre-shared"""
        pass

    def encrypt(self, plaintext: bytes) -> bytes:
        """
        Encrypt with AES-256-GCM

        Returns:
            nonce (12 bytes) + encrypted_data
        """
        nonce = os.urandom(12)  # 12 bytes recommended for GCM
        encrypted_data = self.cipher.encrypt(nonce, plaintext, None)
        return nonce + encrypted_data

    def decrypt(self, ciphertext: bytes) -> bytes:
        """
        Decrypt with AES-256-GCM

        Args:
            ciphertext: nonce (12 bytes) + encrypted_data
        """
        if len(ciphertext) < 12:
            raise ValueError("Ciphertext too short")

        nonce = ciphertext[:12]
        encrypted_data = ciphertext[12:]

        try:
            return self.cipher.decrypt(nonce, encrypted_data, None)
        except InvalidTag:
            raise ValueError("Decryption failed: invalid authentication tag")

    def is_encryption_enabled(self) -> bool:
        return True


class ECDHEncryptionStrategy(EncryptionStrategy):
    """
    ECDH key exchange encryption strategy
    Uses X25519 for key exchange and AES-256-GCM for encryption
    """

    def __init__(self):
        """Initialize ECDH encryption strategy"""
        # Generate ephemeral ECDH key pair
        self.private_key = X25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        self.cipher: Optional[AESGCM] = None

    async def perform_handshake(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        is_server: bool
    ) -> None:
        """
        Perform ECDH key exchange handshake

        Server flow:
        1. Send server's public key
        2. Receive client's public key
        3. Derive shared key

        Client flow:
        1. Receive server's public key
        2. Send client's public key
        3. Derive shared key
        """
        my_pubkey = self._get_public_key_bytes()

        if is_server:
            # Server: send first, then receive
            writer.write(my_pubkey)
            await writer.drain()

            peer_pubkey = await reader.read(32)
            if len(peer_pubkey) != 32:
                raise ValueError("Invalid peer public key size")
        else:
            # Client: receive first, then send
            peer_pubkey = await reader.read(32)
            if len(peer_pubkey) != 32:
                raise ValueError("Invalid peer public key size")

            writer.write(my_pubkey)
            await writer.drain()

        # Derive shared encryption key
        self._derive_shared_key(peer_pubkey)

    def _get_public_key_bytes(self) -> bytes:
        """Export public key as 32 bytes"""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

    def _derive_shared_key(self, peer_public_key_bytes: bytes) -> None:
        """
        Perform ECDH and derive AES key using HKDF

        Args:
            peer_public_key_bytes: Peer's 32-byte X25519 public key
        """
        # Load peer's public key
        peer_public_key = X25519PublicKey.from_public_bytes(peer_public_key_bytes)

        # Perform ECDH to get shared secret
        shared_secret = self.private_key.exchange(peer_public_key)

        # Derive 32-byte AES key using HKDF-SHA256
        kdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b'c2-server-encryption-key',
        )
        derived_key = kdf.derive(shared_secret)

        # Initialize cipher with derived key
        self.cipher = AESGCM(derived_key)

    def encrypt(self, plaintext: bytes) -> bytes:
        """
        Encrypt with AES-256-GCM using derived key

        Returns:
            nonce (12 bytes) + encrypted_data
        """
        if self.cipher is None:
            raise RuntimeError("Encryption not initialized - perform handshake first")

        nonce = os.urandom(12)
        encrypted_data = self.cipher.encrypt(nonce, plaintext, None)
        return nonce + encrypted_data

    def decrypt(self, ciphertext: bytes) -> bytes:
        """
        Decrypt with AES-256-GCM using derived key

        Args:
            ciphertext: nonce (12 bytes) + encrypted_data
        """
        if self.cipher is None:
            raise RuntimeError("Encryption not initialized - perform handshake first")

        if len(ciphertext) < 12:
            raise ValueError("Ciphertext too short")

        nonce = ciphertext[:12]
        encrypted_data = ciphertext[12:]

        try:
            return self.cipher.decrypt(nonce, encrypted_data, None)
        except InvalidTag:
            raise ValueError("Decryption failed: invalid authentication tag")

    def is_encryption_enabled(self) -> bool:
        return True
