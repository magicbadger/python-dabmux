"""
Abstract base class for output destinations.

This module defines the DabOutput abstract class that all output implementations
must inherit from.
"""
from abc import ABC, abstractmethod
from typing import Optional


class DabOutput(ABC):
    """
    Abstract base class for all output destinations.

    Outputs write ETI frames to files, network streams, or other destinations.
    """

    def __init__(self) -> None:
        """Initialize the output."""
        self._is_open = False

    @abstractmethod
    def open(self, name: str) -> None:
        """
        Open the output destination.

        Args:
            name: Destination identifier (filename, URL, etc.)

        Raises:
            RuntimeError: If the destination cannot be opened
            ValueError: If the name is invalid
        """
        pass

    @abstractmethod
    def write(self, data: bytes) -> int:
        """
        Write data to the output.

        Args:
            data: Data bytes to write

        Returns:
            Number of bytes written

        Raises:
            RuntimeError: On write error
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the output destination."""
        pass

    @abstractmethod
    def get_info(self) -> str:
        """
        Get information about this output.

        Returns:
            Human-readable output description (e.g., "file:///path/to/output.eti")
        """
        pass

    @property
    def is_open(self) -> bool:
        """Check if output is open."""
        return self._is_open
