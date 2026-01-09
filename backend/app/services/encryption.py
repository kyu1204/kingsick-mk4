"""
Encryption utilities for KingSick.

Provides AES-256-GCM encryption/decryption for sensitive data like API keys.
"""

import base64
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import get_settings


class EncryptionError(Exception):
    """Raised when encryption or decryption fails."""

    pass


def _get_key() -> bytes:
    """
    Get the encryption key from settings.

    The key must be 32 bytes for AES-256.
    If the key is shorter, it will be padded.
    If longer, it will be truncated.

    Returns:
        bytes: The 32-byte encryption key.
    """
    settings = get_settings()
    key = settings.encryption_key.encode("utf-8")

    # Ensure key is exactly 32 bytes
    if len(key) < 32:
        key = key.ljust(32, b"\0")
    elif len(key) > 32:
        key = key[:32]

    return key


def encrypt(plaintext: str) -> str:
    """
    Encrypt a string using AES-256-GCM.

    The output format is: base64(nonce + ciphertext + tag)
    - nonce: 12 bytes
    - ciphertext: variable length
    - tag: 16 bytes (included in ciphertext by AESGCM)

    Args:
        plaintext: The string to encrypt.

    Returns:
        str: Base64-encoded encrypted data.

    Raises:
        EncryptionError: If encryption fails.
    """
    if not plaintext:
        raise EncryptionError("Cannot encrypt empty string")

    try:
        key = _get_key()
        aesgcm = AESGCM(key)

        # Generate random 12-byte nonce
        nonce = secrets.token_bytes(12)

        # Encrypt the plaintext
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)

        # Combine nonce + ciphertext and encode as base64
        encrypted_data = nonce + ciphertext
        return base64.b64encode(encrypted_data).decode("utf-8")

    except Exception as e:
        raise EncryptionError(f"Encryption failed: {e}") from e


def decrypt(encrypted_data: str) -> str:
    """
    Decrypt a string that was encrypted with AES-256-GCM.

    Args:
        encrypted_data: Base64-encoded encrypted data.

    Returns:
        str: The decrypted plaintext string.

    Raises:
        EncryptionError: If decryption fails (wrong key, corrupted data, etc).
    """
    if not encrypted_data:
        raise EncryptionError("Cannot decrypt empty string")

    try:
        key = _get_key()
        aesgcm = AESGCM(key)

        # Decode from base64
        data = base64.b64decode(encrypted_data)

        # Extract nonce (first 12 bytes) and ciphertext (rest)
        nonce = data[:12]
        ciphertext = data[12:]

        # Decrypt
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")

    except Exception as e:
        raise EncryptionError(f"Decryption failed: {e}") from e


def mask_string(value: str, visible_chars: int = 4) -> str:
    """
    Mask a string, showing only the last N characters.

    Args:
        value: The string to mask.
        visible_chars: Number of characters to show at the end.

    Returns:
        str: Masked string like "****1234".
    """
    if not value:
        return ""

    if len(value) <= visible_chars:
        return "*" * len(value)

    return "*" * (len(value) - visible_chars) + value[-visible_chars:]
