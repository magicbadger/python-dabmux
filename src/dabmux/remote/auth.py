"""
Authentication for remote control.

Provides simple password-based authentication for ZMQ and Telnet interfaces.
"""
import hashlib
import hmac
import structlog
from typing import Optional

logger = structlog.get_logger(__name__)


class Authenticator:
    """
    Simple password-based authenticator.

    Uses SHA-256 hashing with constant-time comparison for security.
    """

    def __init__(
        self,
        password: Optional[str] = None,
        password_hash: Optional[str] = None
    ) -> None:
        """
        Initialize authenticator.

        Args:
            password: Plain text password (will be hashed)
            password_hash: Pre-computed SHA-256 hash (hex format)

        Either password or password_hash must be provided for auth to be enabled.
        """
        if password:
            self.password_hash = self._hash_password(password)
            logger.info("Authentication enabled with password")
        elif password_hash:
            self.password_hash = password_hash
            logger.info("Authentication enabled with pre-hashed password")
        else:
            self.password_hash = None
            logger.info("Authentication disabled (no password configured)")

    def is_enabled(self) -> bool:
        """Check if authentication is enabled."""
        return self.password_hash is not None

    def verify(self, password: str) -> bool:
        """
        Verify password.

        Args:
            password: Password to verify

        Returns:
            True if password matches or auth is disabled, False otherwise

        Uses constant-time comparison to prevent timing attacks.
        """
        if not self.is_enabled():
            return True  # No auth required

        candidate_hash = self._hash_password(password)

        # Use constant-time comparison
        return hmac.compare_digest(candidate_hash, self.password_hash)

    def _hash_password(self, password: str) -> str:
        """
        Hash password using SHA-256.

        Args:
            password: Plain text password

        Returns:
            Hex-encoded SHA-256 hash
        """
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def get_hash(self, password: str) -> str:
        """
        Get hash for a password (utility function).

        Useful for generating password_hash values for configuration.

        Args:
            password: Plain text password

        Returns:
            Hex-encoded SHA-256 hash
        """
        return self._hash_password(password)


def generate_password_hash(password: str) -> str:
    """
    Generate SHA-256 hash for configuration file.

    Args:
        password: Plain text password

    Returns:
        Hash in format suitable for config: "sha256:hexdigest"

    Example:
        >>> hash_str = generate_password_hash("my_password")
        >>> print(hash_str)
        sha256:5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8
    """
    hash_hex = hashlib.sha256(password.encode('utf-8')).hexdigest()
    return f"sha256:{hash_hex}"


def parse_password_hash(hash_str: str) -> str:
    """
    Parse password hash from configuration.

    Args:
        hash_str: Hash string in format "sha256:hexdigest"

    Returns:
        Hex digest portion

    Raises:
        ValueError: If format is invalid
    """
    if not hash_str.startswith("sha256:"):
        raise ValueError("Invalid hash format, expected 'sha256:hexdigest'")

    return hash_str[7:]  # Strip "sha256:" prefix
