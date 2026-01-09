"""
Unit tests for encryption utilities.
"""

import pytest

from app.services.encryption import (
    EncryptionError,
    decrypt,
    encrypt,
    mask_string,
)


class TestEncryption:
    """Tests for encrypt/decrypt functions."""

    def test_encrypt_decrypt_roundtrip(self):
        """Encrypted data should decrypt back to original."""
        original = "my-secret-api-key-12345"
        encrypted = encrypt(original)
        decrypted = decrypt(encrypted)
        assert decrypted == original

    def test_encrypt_produces_different_output_each_time(self):
        """Encryption should produce different output each time (random nonce)."""
        original = "same-input"
        encrypted1 = encrypt(original)
        encrypted2 = encrypt(original)
        assert encrypted1 != encrypted2

    def test_encrypt_empty_string_raises_error(self):
        """Encrypting empty string should raise error."""
        with pytest.raises(EncryptionError, match="Cannot encrypt empty string"):
            encrypt("")

    def test_decrypt_empty_string_raises_error(self):
        """Decrypting empty string should raise error."""
        with pytest.raises(EncryptionError, match="Cannot decrypt empty string"):
            decrypt("")

    def test_decrypt_invalid_data_raises_error(self):
        """Decrypting invalid data should raise error."""
        with pytest.raises(EncryptionError, match="Decryption failed"):
            decrypt("invalid-base64-data!")

    def test_decrypt_corrupted_data_raises_error(self):
        """Decrypting corrupted data should raise error."""
        original = "test-data"
        encrypted = encrypt(original)
        # Corrupt the encrypted data by changing some characters
        corrupted = encrypted[:-5] + "XXXXX"
        with pytest.raises(EncryptionError, match="Decryption failed"):
            decrypt(corrupted)

    def test_encrypt_special_characters(self):
        """Encryption should handle special characters."""
        original = "특수문자!@#$%^&*()_+한글テスト"
        encrypted = encrypt(original)
        decrypted = decrypt(encrypted)
        assert decrypted == original

    def test_encrypt_long_string(self):
        """Encryption should handle long strings."""
        original = "x" * 10000
        encrypted = encrypt(original)
        decrypted = decrypt(encrypted)
        assert decrypted == original


class TestMaskString:
    """Tests for mask_string function."""

    def test_mask_string_default(self):
        """Mask string should show last 4 characters by default."""
        result = mask_string("1234567890")
        assert result == "******7890"

    def test_mask_string_custom_visible_chars(self):
        """Mask string should respect custom visible_chars."""
        result = mask_string("1234567890", visible_chars=2)
        assert result == "********90"

    def test_mask_string_short_input(self):
        """Short strings should be fully masked."""
        result = mask_string("123", visible_chars=4)
        assert result == "***"

    def test_mask_string_empty(self):
        """Empty string should return empty string."""
        result = mask_string("")
        assert result == ""

    def test_mask_string_exact_length(self):
        """String equal to visible_chars should be fully masked."""
        result = mask_string("1234", visible_chars=4)
        assert result == "****"
