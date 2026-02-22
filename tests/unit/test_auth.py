"""
Unit tests for authentication module.
"""
import pytest
from dabmux.remote.auth import Authenticator, generate_password_hash, parse_password_hash


class TestAuthenticator:
    """Tests for Authenticator class."""

    def test_create_with_password(self):
        """Test creating authenticator with plain text password."""
        auth = Authenticator(password="test_password")
        assert auth.is_enabled()
        assert auth.password_hash is not None

    def test_create_with_hash(self):
        """Test creating authenticator with pre-hashed password."""
        password_hash = "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"
        auth = Authenticator(password_hash=password_hash)
        assert auth.is_enabled()
        assert auth.password_hash == password_hash

    def test_create_disabled(self):
        """Test creating disabled authenticator (no password)."""
        auth = Authenticator()
        assert not auth.is_enabled()

    def test_verify_correct_password(self):
        """Test verifying correct password."""
        auth = Authenticator(password="test_password")
        assert auth.verify("test_password")

    def test_verify_incorrect_password(self):
        """Test verifying incorrect password."""
        auth = Authenticator(password="test_password")
        assert not auth.verify("wrong_password")

    def test_verify_disabled_auth(self):
        """Test verify returns True when auth is disabled."""
        auth = Authenticator()
        assert auth.verify("any_password")

    def test_hash_consistency(self):
        """Test that same password produces same hash."""
        auth = Authenticator(password="test")
        hash1 = auth._hash_password("test")
        hash2 = auth._hash_password("test")
        assert hash1 == hash2

    def test_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes."""
        auth = Authenticator()
        hash1 = auth._hash_password("password1")
        hash2 = auth._hash_password("password2")
        assert hash1 != hash2

    def test_generate_password_hash(self):
        """Test generate_password_hash utility function."""
        hash_str = generate_password_hash("my_password")
        assert hash_str.startswith("sha256:")
        assert len(hash_str) > 70  # sha256: + 64 hex chars

    def test_parse_password_hash(self):
        """Test parse_password_hash utility function."""
        hash_str = "sha256:abc123def456"
        parsed = parse_password_hash(hash_str)
        assert parsed == "abc123def456"

    def test_parse_password_hash_invalid(self):
        """Test parse_password_hash with invalid format."""
        with pytest.raises(ValueError, match="Invalid hash format"):
            parse_password_hash("invalid_format")

    def test_get_hash(self):
        """Test get_hash utility method."""
        auth = Authenticator()
        hash1 = auth.get_hash("password")
        hash2 = auth._hash_password("password")
        assert hash1 == hash2
