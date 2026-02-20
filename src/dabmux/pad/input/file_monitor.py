"""
File monitor input for DLS updates.

Monitors a text file for modifications and provides DLS text updates.
"""

import time
from pathlib import Path
from typing import Optional
import structlog

from dabmux.pad.base import PADInput

logger = structlog.get_logger(__name__)


class FileMonitorInput(PADInput):
    """
    Monitor a text file for DLS updates.

    Reads file content when modified and provides to DLS encoder.
    Uses file modification time for efficient polling.

    The file should contain a single line of text (or the first line
    will be used if multiple lines are present).
    """

    def __init__(self, file_path: str, poll_interval: float = 1.0):
        """
        Initialize file monitor.

        Args:
            file_path: Path to text file to monitor
            poll_interval: Seconds between file checks (default: 1.0)
        """
        self.file_path = Path(file_path)
        self.poll_interval = poll_interval
        self.last_mtime: Optional[float] = None
        self.last_content: str = ""
        self.last_check_time: float = 0

        logger.info("File monitor initialized",
                   path=str(self.file_path),
                   poll_interval=poll_interval)

        # Do initial file read
        if self.file_path.exists():
            try:
                self.last_mtime = self.file_path.stat().st_mtime
                self.last_content = self._read_file()
                if self.last_content:
                    logger.info("Initial DLS loaded from file",
                              path=str(self.file_path),
                              text=self.last_content[:50])
            except Exception as e:
                logger.warning("Could not read DLS file on initialization",
                             path=str(self.file_path),
                             error=str(e))

    def get_dls_text(self) -> Optional[str]:
        """
        Get current DLS text from file.

        Returns:
            DLS text string, or None if no text available
        """
        return self.last_content if self.last_content else None

    def update(self) -> bool:
        """
        Check file for modifications and update content.

        Non-blocking operation that checks file modification time
        and reads content if changed.

        Returns:
            True if content changed, False otherwise
        """
        current_time = time.time()

        # Rate limit checks to poll_interval
        if current_time - self.last_check_time < self.poll_interval:
            return False

        self.last_check_time = current_time

        # Check if file exists
        if not self.file_path.exists():
            if self.last_content:
                logger.warning("DLS file disappeared", path=str(self.file_path))
                self.last_content = ""
                self.last_mtime = None
                return True
            return False

        # Check modification time
        try:
            mtime = self.file_path.stat().st_mtime

            # If mtime hasn't changed, no update needed
            if self.last_mtime is not None and mtime == self.last_mtime:
                return False

            self.last_mtime = mtime

            # Read file content
            content = self._read_file()

            if content != self.last_content:
                logger.info("DLS updated from file",
                          path=str(self.file_path),
                          text=content[:50] if content else "(empty)")
                self.last_content = content
                return True

            return False

        except PermissionError:
            logger.error("Permission denied reading DLS file",
                        path=str(self.file_path))
            return False
        except Exception as e:
            logger.error("Error checking DLS file",
                        path=str(self.file_path),
                        error=str(e))
            return False

    def _read_file(self) -> str:
        """
        Read and process file content.

        Reads the file, takes only the first line, and trims whitespace.

        Returns:
            Processed text (single line, trimmed)
        """
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            # Take only first line if multi-line
            if '\n' in content:
                content = content.split('\n')[0].strip()

            return content

        except UnicodeDecodeError:
            logger.error("DLS file encoding error (not UTF-8)",
                        path=str(self.file_path))
            return ""
        except Exception as e:
            logger.error("Error reading DLS file",
                        path=str(self.file_path),
                        error=str(e))
            return ""

    def close(self) -> None:
        """Close file monitor and cleanup resources."""
        # No resources to cleanup for file monitoring
        logger.info("File monitor closed", path=str(self.file_path))
