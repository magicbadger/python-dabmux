"""Tests for DLS file monitor input."""

import pytest
import tempfile
import time
from pathlib import Path

from dabmux.pad.input.file_monitor import FileMonitorInput


class TestFileMonitorInput:
    """Test file monitoring for DLS updates."""

    def test_file_monitor_initialization(self):
        """Test file monitor initialization."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name

        try:
            monitor = FileMonitorInput(temp_path, poll_interval=0.1)
            assert monitor.file_path == Path(temp_path)
            assert monitor.poll_interval == 0.1
            assert monitor.get_dls_text() is None
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_file_monitor_initial_read(self):
        """Test initial file reading."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("Initial text")
            f.flush()
            temp_path = f.name

        try:
            # Initial read happens in __init__
            monitor = FileMonitorInput(temp_path, poll_interval=0.1)

            # Text should be available immediately
            assert monitor.get_dls_text() == "Initial text"

            # First update() returns False (no change since init)
            changed = monitor.update()
            assert not changed
        finally:
            Path(temp_path).unlink()

    def test_file_monitor_update_detection(self):
        """Test file modification detection."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("First")
            f.flush()
            temp_path = f.name

        try:
            monitor = FileMonitorInput(temp_path, poll_interval=0.1)
            monitor.update()
            assert monitor.get_dls_text() == "First"

            # Modify file
            time.sleep(0.2)  # Ensure mtime changes
            with open(temp_path, 'w') as f:
                f.write("Second")

            # Check for update
            time.sleep(0.1)  # Wait for poll interval
            changed = monitor.update()
            assert changed
            assert monitor.get_dls_text() == "Second"
        finally:
            Path(temp_path).unlink()

    def test_file_monitor_no_change(self):
        """Test that no update is detected when file unchanged."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("Unchanged")
            f.flush()
            temp_path = f.name

        try:
            monitor = FileMonitorInput(temp_path, poll_interval=0.1)
            monitor.update()

            # Check again immediately (within poll interval)
            changed = monitor.update()
            assert not changed

            # Wait for poll interval and check again (still no change)
            time.sleep(0.15)
            changed = monitor.update()
            assert not changed  # File not modified
        finally:
            Path(temp_path).unlink()

    def test_file_monitor_multiline(self):
        """Test that only first line is used."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("Line 1\nLine 2\nLine 3")
            f.flush()
            temp_path = f.name

        try:
            monitor = FileMonitorInput(temp_path, poll_interval=0.1)
            monitor.update()

            assert monitor.get_dls_text() == "Line 1"
        finally:
            Path(temp_path).unlink()

    def test_file_monitor_whitespace_trimming(self):
        """Test whitespace trimming."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("  Trimmed Text  \n")
            f.flush()
            temp_path = f.name

        try:
            monitor = FileMonitorInput(temp_path, poll_interval=0.1)
            monitor.update()

            assert monitor.get_dls_text() == "Trimmed Text"
        finally:
            Path(temp_path).unlink()

    def test_file_monitor_empty_file(self):
        """Test empty file handling."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("")
            f.flush()
            temp_path = f.name

        try:
            monitor = FileMonitorInput(temp_path, poll_interval=0.1)
            changed = monitor.update()

            # Empty file should result in no content change if starting empty
            assert monitor.get_dls_text() in [None, ""]
        finally:
            Path(temp_path).unlink()

    def test_file_monitor_file_disappears(self):
        """Test handling when file is deleted."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("Temporary")
            f.flush()
            temp_path = f.name

        monitor = FileMonitorInput(temp_path, poll_interval=0.1)
        monitor.update()
        assert monitor.get_dls_text() == "Temporary"

        # Delete file
        Path(temp_path).unlink()

        # Check after deletion
        time.sleep(0.15)
        changed = monitor.update()

        # Should detect disappearance
        assert changed
        assert monitor.get_dls_text() in [None, ""]

    def test_file_monitor_nonexistent_file(self):
        """Test with file that doesn't exist initially."""
        temp_path = "/tmp/nonexistent_dls_test_file.txt"

        monitor = FileMonitorInput(temp_path, poll_interval=0.1)
        changed = monitor.update()

        # Should not crash, just return False
        assert not changed
        assert monitor.get_dls_text() is None

    def test_file_monitor_utf8_content(self):
        """Test UTF-8 content handling."""
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False) as f:
            f.write("Héllo Wörld 世界 ♫")
            f.flush()
            temp_path = f.name

        try:
            monitor = FileMonitorInput(temp_path, poll_interval=0.1)
            monitor.update()

            assert monitor.get_dls_text() == "Héllo Wörld 世界 ♫"
        finally:
            Path(temp_path).unlink()

    def test_file_monitor_poll_interval(self):
        """Test poll interval rate limiting."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("Test")
            f.flush()
            temp_path = f.name

        try:
            monitor = FileMonitorInput(temp_path, poll_interval=0.5)

            # Initial text loaded in __init__
            assert monitor.get_dls_text() == "Test"

            # First update returns False (no change since init)
            assert not monitor.update()

            # Immediate second update should also be rate-limited
            assert not monitor.update()

            # After waiting and modifying file, should detect change
            time.sleep(0.6)
            with open(temp_path, 'w') as f:
                f.write("Modified")
            time.sleep(0.1)

            assert monitor.update()
            assert monitor.get_dls_text() == "Modified"
        finally:
            Path(temp_path).unlink()

    def test_file_monitor_rapid_updates(self):
        """Test multiple rapid file updates."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("Initial")
            f.flush()
            temp_path = f.name

        try:
            monitor = FileMonitorInput(temp_path, poll_interval=0.1)
            monitor.update()

            # Perform several updates
            for i in range(5):
                time.sleep(0.15)
                with open(temp_path, 'w') as f:
                    f.write(f"Update {i}")
                time.sleep(0.05)

                changed = monitor.update()
                assert changed or i == 0  # First might not change if too fast
                if changed:
                    assert f"Update" in monitor.get_dls_text()

        finally:
            Path(temp_path).unlink()
