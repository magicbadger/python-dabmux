"""
Base classes for PAD (Programme Associated Data) encoding.

PAD carries supplementary information alongside audio data, including:
- DLS (Dynamic Label Segment) - text information
- MOT Slideshow - images
- Other data services
"""

from abc import ABC, abstractmethod
from typing import Optional


class PADEncoder(ABC):
    """
    Base class for PAD encoders.

    PAD encoders generate Programme Associated Data to be transmitted
    with the audio stream.
    """

    @abstractmethod
    def encode(self) -> bytes:
        """
        Encode PAD data for current frame.

        Returns:
            PAD data bytes
        """
        pass

    @abstractmethod
    def get_length(self) -> int:
        """
        Get PAD length in bytes.

        Returns:
            PAD length (typically 20-58 bytes depending on bitrate)
        """
        pass


class PADInput(ABC):
    """
    Base class for PAD input sources.

    PAD inputs provide data to be encoded, such as DLS text from files,
    FIFOs, or network sources.
    """

    @abstractmethod
    def get_dls_text(self) -> Optional[str]:
        """
        Get current DLS text.

        Returns:
            DLS text string, or None if no text available
        """
        pass

    @abstractmethod
    def update(self) -> bool:
        """
        Check for updates and refresh internal state (non-blocking).

        Returns:
            True if content changed, False otherwise
        """
        pass
