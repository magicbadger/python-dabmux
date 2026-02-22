"""
Unit tests for MOT Carousel Manager.

Tests carousel management, priority scheduling, and directory monitoring.
"""

import pytest
import tempfile
import time
from pathlib import Path
from dabmux.mot.carousel import CarouselManager, CarouselState, WATCHDOG_AVAILABLE


class TestCarouselState:
    """Tests for CarouselState dataclass."""

    def test_state_creation(self):
        """Test creating carousel state."""
        state = CarouselState()

        assert state.current_packet_index == 0
        assert state.total_transmissions == 0
        assert state.last_transmission_time == 0.0
        assert len(state.packets) == 0

    def test_state_with_packets(self):
        """Test state with packets."""
        from dabmux.mot.msc_packet import MscPacket

        packets = [
            MscPacket(
                address=0,
                useful_data_length=10,
                continuity_index=0,
                first=True,
                last=True,
                data=b'test'
            )
        ]

        state = CarouselState(packets=packets)

        assert len(state.packets) == 1


class TestCarouselManager:
    """Tests for CarouselManager."""

    def create_test_carousel_dir(self, tmp_path):
        """
        Create test carousel directory with sample files.

        Creates:
        - slide01.jpg (high priority, enabled)
        - slide02.png (medium priority, enabled)
        - slide03.gif (low priority, disabled)
        """
        carousel_dir = tmp_path / "carousel"
        carousel_dir.mkdir()

        # Slide 1: JPEG, priority 8, enabled
        slide1 = carousel_dir / "slide01.jpg"
        slide1.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        slide1_meta = carousel_dir / "slide01.yaml"
        slide1_meta.write_text("""
transport_id: 1
priority: 8
enabled: true
content_type: "image/jpeg"
content_name: "Slide 1"
category_id: 1
slide_id: 1
""")

        # Slide 2: PNG, priority 5, enabled
        slide2 = carousel_dir / "slide02.png"
        slide2.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)

        slide2_meta = carousel_dir / "slide02.yaml"
        slide2_meta.write_text("""
transport_id: 2
priority: 5
enabled: true
content_type: "image/png"
content_name: "Slide 2"
category_id: 1
slide_id: 2
""")

        # Slide 3: GIF, priority 3, disabled
        slide3 = carousel_dir / "slide03.gif"
        slide3.write_bytes(b'GIF89a' + b'\x00' * 100)

        slide3_meta = carousel_dir / "slide03.yaml"
        slide3_meta.write_text("""
transport_id: 3
priority: 3
enabled: false
content_type: "image/gif"
content_name: "Slide 3"
category_id: 1
slide_id: 3
""")

        return carousel_dir

    def test_carousel_creation(self, tmp_path):
        """Test creating carousel manager."""
        carousel_dir = self.create_test_carousel_dir(tmp_path)

        carousel = CarouselManager(
            directory=str(carousel_dir),
            address=10,
            max_packet_size=96,
            enable_watching=False
        )

        assert carousel.directory == carousel_dir
        assert carousel.address == 10
        assert carousel.max_packet_size == 96

    def test_carousel_missing_directory(self):
        """Test error when directory doesn't exist."""
        with pytest.raises(FileNotFoundError):
            CarouselManager(
                directory="/nonexistent/carousel",
                enable_watching=False
            )

    def test_carousel_loads_objects(self, tmp_path):
        """Test carousel loads objects from directory."""
        carousel_dir = self.create_test_carousel_dir(tmp_path)

        carousel = CarouselManager(
            directory=str(carousel_dir),
            enable_watching=False
        )

        # Should load 2 enabled objects + 1 directory = 3 total
        assert len(carousel.objects) == 3

        # Check directory object (transport_id=0)
        assert 0 in carousel.objects
        dir_obj = carousel.objects[0]
        assert dir_obj.transport_id == 0

        # Check enabled objects
        assert 1 in carousel.objects  # slide01
        assert 2 in carousel.objects  # slide02
        assert 3 not in carousel.objects  # slide03 (disabled)

    def test_carousel_generates_packets(self, tmp_path):
        """Test carousel generates packets for objects."""
        carousel_dir = self.create_test_carousel_dir(tmp_path)

        carousel = CarouselManager(
            directory=str(carousel_dir),
            enable_watching=False
        )

        # All objects should have packets
        for transport_id in carousel.objects:
            assert transport_id in carousel.states
            state = carousel.states[transport_id]
            assert len(state.packets) > 0

    def test_carousel_priority_queues(self, tmp_path):
        """Test carousel builds priority queues."""
        carousel_dir = self.create_test_carousel_dir(tmp_path)

        carousel = CarouselManager(
            directory=str(carousel_dir),
            enable_watching=False
        )

        # Priority 8: directory (0) + slide01 (1)
        assert 0 in carousel.priority_queues[8]
        assert 1 in carousel.priority_queues[8]

        # Priority 5: slide02 (2)
        assert 2 in carousel.priority_queues[5]

        # Priority 3: empty (slide03 disabled)
        assert len(carousel.priority_queues[3]) == 0

    def test_carousel_directory_first_in_priority(self, tmp_path):
        """Test directory object is first in highest priority."""
        carousel_dir = self.create_test_carousel_dir(tmp_path)

        carousel = CarouselManager(
            directory=str(carousel_dir),
            enable_watching=False
        )

        # Directory should be first in priority 8
        assert carousel.priority_queues[8][0] == 0

    def test_get_next_packet(self, tmp_path):
        """Test getting next packet from carousel."""
        carousel_dir = self.create_test_carousel_dir(tmp_path)

        carousel = CarouselManager(
            directory=str(carousel_dir),
            enable_watching=False
        )

        # Get first packet
        packet = carousel.get_next_packet()

        assert packet is not None
        assert packet.address == 0

    def test_get_next_packet_round_robin(self, tmp_path):
        """Test round-robin packet scheduling."""
        carousel_dir = self.create_test_carousel_dir(tmp_path)

        carousel = CarouselManager(
            directory=str(carousel_dir),
            enable_watching=False
        )

        # Get packets and track which objects they come from
        # by checking transmission counts
        initial_counts = {
            tid: carousel.states[tid].total_transmissions
            for tid in carousel.objects
        }

        # Get many packets
        for _ in range(100):
            packet = carousel.get_next_packet()
            assert packet is not None

        # All objects should have transmitted at least once
        for transport_id in carousel.objects:
            state = carousel.states[transport_id]
            assert state.total_transmissions > initial_counts[transport_id]

    def test_get_next_packet_priority_ordering(self, tmp_path):
        """Test higher priority objects transmit more frequently."""
        carousel_dir = self.create_test_carousel_dir(tmp_path)

        carousel = CarouselManager(
            directory=str(carousel_dir),
            enable_watching=False
        )

        # Transmit many packets
        for _ in range(500):
            carousel.get_next_packet()

        # Higher priority objects should have more transmissions
        # Priority 8 objects (directory=0, slide01=1)
        p8_transmissions = sum(
            carousel.states[tid].total_transmissions
            for tid in carousel.priority_queues[8]
        )

        # Priority 5 objects (slide02=2)
        p5_transmissions = sum(
            carousel.states[tid].total_transmissions
            for tid in carousel.priority_queues[5]
        )

        # Priority 8 should have more transmissions than priority 5
        assert p8_transmissions > p5_transmissions

    def test_get_next_packet_wraps_object_packets(self, tmp_path):
        """Test packet index wraps within object."""
        carousel_dir = self.create_test_carousel_dir(tmp_path)

        carousel = CarouselManager(
            directory=str(carousel_dir),
            enable_watching=False
        )

        # Get transport_id with multiple packets
        transport_id = 0  # Directory
        state = carousel.states[transport_id]
        num_packets = len(state.packets)

        # Transmit enough to wrap (extra +1 to trigger the wrap)
        for _ in range(num_packets * 3 + 1):
            carousel.get_next_packet()

        # Packet index should have wrapped (0 or 1 for 2-packet object)
        assert state.current_packet_index <= 1

    def test_get_next_packet_empty_carousel(self, tmp_path):
        """Test get_next_packet with empty carousel."""
        carousel_dir = tmp_path / "empty_carousel"
        carousel_dir.mkdir()

        carousel = CarouselManager(
            directory=str(carousel_dir),
            enable_watching=False
        )

        # Empty carousel (only directory, but it's empty)
        # Should still have directory object
        packet = carousel.get_next_packet()

        # Directory object should exist even if no other objects
        assert packet is not None

    def test_reload(self, tmp_path):
        """Test reloading carousel."""
        carousel_dir = self.create_test_carousel_dir(tmp_path)

        carousel = CarouselManager(
            directory=str(carousel_dir),
            enable_watching=False
        )

        initial_count = len(carousel.objects)

        # Add new file
        slide4 = carousel_dir / "slide04.jpg"
        slide4.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        slide4_meta = carousel_dir / "slide04.yaml"
        slide4_meta.write_text("""
transport_id: 4
priority: 6
enabled: true
content_type: "image/jpeg"
content_name: "Slide 4"
""")

        # Reload
        carousel.reload()

        # Should have one more object
        assert len(carousel.objects) == initial_count + 1
        assert 4 in carousel.objects

    def test_reload_removes_deleted_objects(self, tmp_path):
        """Test reload removes deleted objects."""
        carousel_dir = self.create_test_carousel_dir(tmp_path)

        carousel = CarouselManager(
            directory=str(carousel_dir),
            enable_watching=False
        )

        assert 1 in carousel.objects

        # Delete slide01
        (carousel_dir / "slide01.jpg").unlink()
        (carousel_dir / "slide01.yaml").unlink()

        # Reload
        carousel.reload()

        # Object should be removed
        assert 1 not in carousel.objects

    def test_reload_updates_modified_objects(self, tmp_path):
        """Test reload updates modified objects."""
        carousel_dir = self.create_test_carousel_dir(tmp_path)

        carousel = CarouselManager(
            directory=str(carousel_dir),
            enable_watching=False
        )

        # Check initial priority
        assert carousel.objects[1].priority == 8

        # Modify metadata
        slide1_meta = carousel_dir / "slide01.yaml"
        slide1_meta.write_text("""
transport_id: 1
priority: 2
enabled: true
content_type: "image/jpeg"
content_name: "Slide 1"
""")

        # Reload
        carousel.reload()

        # Priority should be updated
        assert carousel.objects[1].priority == 2
        assert 1 in carousel.priority_queues[2]
        assert 1 not in carousel.priority_queues[8]

    def test_get_statistics(self, tmp_path):
        """Test getting carousel statistics."""
        carousel_dir = self.create_test_carousel_dir(tmp_path)

        carousel = CarouselManager(
            directory=str(carousel_dir),
            enable_watching=False
        )

        # Transmit some packets
        for _ in range(50):
            carousel.get_next_packet()

        # Get statistics
        stats = carousel.get_statistics()

        assert stats['directory'] == str(carousel_dir)
        assert stats['total_objects'] == 3  # directory + 2 enabled slides
        assert stats['total_packets'] > 0
        assert stats['total_transmissions'] == 50
        assert 'priority_distribution' in stats
        assert 'objects' in stats

        # Check object statistics
        assert len(stats['objects']) == 3

    def test_carousel_without_metadata(self, tmp_path):
        """Test carousel skips files without metadata."""
        carousel_dir = tmp_path / "carousel"
        carousel_dir.mkdir()

        # Image without metadata
        (carousel_dir / "nometa.jpg").write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        carousel = CarouselManager(
            directory=str(carousel_dir),
            enable_watching=False
        )

        # Should only have directory object
        assert len(carousel.objects) == 1
        assert 0 in carousel.objects

    @pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not installed")
    def test_start_stop_watching(self, tmp_path):
        """Test starting and stopping directory watching."""
        carousel_dir = self.create_test_carousel_dir(tmp_path)

        carousel = CarouselManager(
            directory=str(carousel_dir),
            enable_watching=True
        )

        # Observer should be running
        assert carousel.observer is not None
        assert carousel.observer.is_alive()

        # Stop watching
        carousel.stop_watching()

        # Observer should be stopped
        assert carousel.observer is None

    @pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not installed")
    def test_hot_reload_on_file_change(self, tmp_path):
        """Test hot-reload when file changes."""
        carousel_dir = self.create_test_carousel_dir(tmp_path)

        carousel = CarouselManager(
            directory=str(carousel_dir),
            enable_watching=True
        )

        initial_count = len(carousel.objects)

        # Wait for observer to start
        time.sleep(0.1)

        # Add new file
        slide4 = carousel_dir / "slide04.jpg"
        slide4.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        slide4_meta = carousel_dir / "slide04.yaml"
        slide4_meta.write_text("""
transport_id: 4
priority: 7
enabled: true
content_type: "image/jpeg"
content_name: "Slide 4"
""")

        # Wait for file system event
        time.sleep(0.5)

        # Should have reloaded automatically
        assert len(carousel.objects) > initial_count

        carousel.stop_watching()

    def test_carousel_disabled_watching(self, tmp_path):
        """Test carousel with watching disabled."""
        carousel_dir = self.create_test_carousel_dir(tmp_path)

        carousel = CarouselManager(
            directory=str(carousel_dir),
            enable_watching=False
        )

        # Observer should not be started
        assert carousel.observer is None

    def test_state_transmission_time_tracking(self, tmp_path):
        """Test state tracks last transmission time."""
        carousel_dir = self.create_test_carousel_dir(tmp_path)

        carousel = CarouselManager(
            directory=str(carousel_dir),
            enable_watching=False
        )

        # Initial transmission times should be 0
        for state in carousel.states.values():
            assert state.last_transmission_time == 0.0

        # Get packet
        carousel.get_next_packet()

        # At least one object should have updated time
        updated = any(
            state.last_transmission_time > 0.0
            for state in carousel.states.values()
        )
        assert updated

    def test_carousel_handles_invalid_metadata(self, tmp_path):
        """Test carousel handles invalid metadata gracefully."""
        carousel_dir = tmp_path / "carousel"
        carousel_dir.mkdir()

        # Valid image
        slide1 = carousel_dir / "slide01.jpg"
        slide1.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        # Invalid YAML
        slide1_meta = carousel_dir / "slide01.yaml"
        slide1_meta.write_text("invalid: yaml: syntax: error:")

        # Should not crash
        carousel = CarouselManager(
            directory=str(carousel_dir),
            enable_watching=False
        )

        # Should only have directory
        assert len(carousel.objects) == 1
