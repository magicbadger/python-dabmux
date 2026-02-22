"""
MOT Carousel Manager.

Provides directory-based carousel management with:
- File watching for hot-reload
- Priority-based scheduling (1-8)
- Automatic directory object generation
- Transmission state tracking

Per ETSI TS 101 499 (MOT) and user requirements.
"""

import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
import structlog

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = object
    FileSystemEvent = object

from dabmux.mot.object import MotObject
from dabmux.mot.directory import MotDirectory
from dabmux.mot.msc_packet import MscPacket, packetize_mot_object

logger = structlog.get_logger(__name__)


@dataclass
class CarouselState:
    """
    Tracks transmission state for carousel objects.

    Per-object state includes:
    - Current packet index
    - Total transmissions
    - Last transmission time
    """
    current_packet_index: int = 0
    total_transmissions: int = 0
    last_transmission_time: float = 0.0
    packets: List[MscPacket] = field(default_factory=list)


class CarouselFileHandler(FileSystemEventHandler):
    """
    Handles file system events for carousel directory.

    Triggers carousel reload on:
    - New files (.jpg, .png, .gif, .bmp, .yaml)
    - Modified files
    - Deleted files
    """

    def __init__(self, carousel_manager):
        """
        Initialize handler.

        Args:
            carousel_manager: CarouselManager instance to notify
        """
        self.carousel_manager = carousel_manager
        self.monitored_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.yaml', '.yml'}

    def _is_monitored_file(self, path: str) -> bool:
        """Check if file should trigger reload."""
        return Path(path).suffix.lower() in self.monitored_extensions

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation."""
        if not event.is_directory and self._is_monitored_file(event.src_path):
            logger.info("Carousel file created", path=event.src_path)
            self.carousel_manager.reload()

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification."""
        if not event.is_directory and self._is_monitored_file(event.src_path):
            logger.info("Carousel file modified", path=event.src_path)
            self.carousel_manager.reload()

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion."""
        if not event.is_directory and self._is_monitored_file(event.src_path):
            logger.info("Carousel file deleted", path=event.src_path)
            self.carousel_manager.reload()


class CarouselManager:
    """
    Manages MOT carousel with directory monitoring and priority scheduling.

    Features:
    - Loads MOT objects from directory
    - Monitors directory for changes (optional, requires watchdog)
    - Priority-based packet scheduling (1-8)
    - Automatic directory object generation
    - Hot-reload support

    Directory structure:
        carousel_dir/
            slide01.jpg
            slide01.yaml        # Metadata for slide01.jpg
            slide02.png
            slide02.yaml
            epg_si.dat
            epg_si.yaml

    Metadata YAML format:
        transport_id: 1
        priority: 5
        enabled: true
        content_type: "image/jpeg"
        category_id: 1
        slide_id: 1
        trigger_time: 5000
    """

    def __init__(
        self,
        directory: str,
        address: int = 0,
        max_packet_size: int = 96,
        enable_watching: bool = True
    ):
        """
        Initialize carousel manager.

        Args:
            directory: Path to carousel directory
            address: Packet address (0-1023)
            max_packet_size: Maximum packet size in bytes
            enable_watching: Enable directory watching (requires watchdog)

        Raises:
            FileNotFoundError: If directory doesn't exist
            ImportError: If enable_watching=True but watchdog not installed
        """
        # Initialize observer first for cleanup in case of errors
        self.observer = None

        self.directory = Path(directory)
        if not self.directory.exists():
            raise FileNotFoundError(f"Carousel directory not found: {directory}")

        self.address = address
        self.max_packet_size = max_packet_size

        # MOT objects and directory
        self.mot_directory = MotDirectory()
        self.objects: Dict[int, MotObject] = {}  # transport_id -> object
        self.states: Dict[int, CarouselState] = {}  # transport_id -> state

        # Priority scheduling
        self.priority_queues: Dict[int, List[int]] = {
            p: [] for p in range(1, 9)
        }  # priority -> [transport_ids]
        self.current_priority = 8  # Start with highest priority
        self.current_index_in_priority = 0

        # Directory watching
        self.enable_watching = enable_watching and WATCHDOG_AVAILABLE

        if enable_watching and not WATCHDOG_AVAILABLE:
            logger.warning(
                "Directory watching requested but watchdog not installed. "
                "Install with: pip install watchdog"
            )

        # Load initial objects
        self.reload()

        # Start watching if enabled
        if self.enable_watching:
            self.start_watching()

    def reload(self) -> None:
        """
        Reload carousel from directory.

        Steps:
        1. Scan directory for MOT objects
        2. Load objects with metadata
        3. Generate directory object
        4. Packetize all objects
        5. Rebuild priority queues
        """
        logger.info("Reloading carousel", directory=str(self.directory))

        # Clear existing state
        old_objects = set(self.objects.keys())
        self.objects.clear()
        self.states.clear()
        self.mot_directory = MotDirectory()
        for p in range(1, 9):
            self.priority_queues[p].clear()

        # Scan directory for objects
        loaded_objects = self._scan_directory()

        # Add enabled objects to directory and carousel
        for obj in loaded_objects:
            if obj.enabled:
                self.mot_directory.add_object(obj)
                self.objects[obj.transport_id] = obj
                self.priority_queues[obj.priority].append(obj.transport_id)

        # Generate and add directory object (always transport_id=0, priority=8)
        dir_obj = self.mot_directory.encode_directory_object()
        self.objects[0] = dir_obj
        self.priority_queues[8].insert(0, 0)  # Directory first in highest priority

        # Packetize all objects
        for transport_id, obj in self.objects.items():
            packets = packetize_mot_object(
                obj,
                address=self.address,
                max_packet_size=self.max_packet_size
            )

            self.states[transport_id] = CarouselState(
                current_packet_index=0,
                total_transmissions=0,
                last_transmission_time=0.0,
                packets=packets
            )

        # Log statistics
        new_objects = set(self.objects.keys())
        added = new_objects - old_objects
        removed = old_objects - new_objects

        logger.info(
            "Carousel reloaded",
            total_objects=len(self.objects),
            directory_packets=len(self.states[0].packets) if 0 in self.states else 0,
            added=len(added),
            removed=len(removed)
        )

    def _scan_directory(self) -> List[MotObject]:
        """
        Scan directory for MOT objects.

        Looks for image files and data files with corresponding .yaml metadata.

        Returns:
            List of MotObject instances
        """
        objects = []
        processed_files: Set[str] = set()

        # Scan for files
        for file_path in self.directory.iterdir():
            if file_path.is_dir():
                continue

            # Skip already processed files
            if str(file_path) in processed_files:
                continue

            # Skip metadata files (will be loaded with their objects)
            if file_path.suffix.lower() in {'.yaml', '.yml'}:
                continue

            # Check for metadata file
            metadata_path = file_path.with_suffix('.yaml')
            if not metadata_path.exists():
                metadata_path = file_path.with_suffix('.yml')
                if not metadata_path.exists():
                    logger.warning(
                        "No metadata file found, skipping",
                        file=str(file_path)
                    )
                    continue

            # Load object with metadata
            try:
                obj = MotObject.from_file(
                    file_path=str(file_path),
                    metadata_path=str(metadata_path)
                )
                objects.append(obj)
                processed_files.add(str(file_path))
                processed_files.add(str(metadata_path))

                logger.debug(
                    "Loaded MOT object",
                    file=file_path.name,
                    transport_id=obj.transport_id,
                    priority=obj.priority,
                    enabled=obj.enabled
                )

            except Exception as e:
                logger.error(
                    "Failed to load MOT object",
                    file=str(file_path),
                    error=str(e)
                )

        return objects

    def start_watching(self) -> None:
        """Start watching directory for changes."""
        if not self.enable_watching:
            logger.warning("Directory watching not enabled")
            return

        if self.observer is not None:
            logger.warning("Directory watching already started")
            return

        try:
            self.observer = Observer()
            handler = CarouselFileHandler(self)
            self.observer.schedule(handler, str(self.directory), recursive=False)
            self.observer.start()

            logger.info("Directory watching started", directory=str(self.directory))

        except Exception as e:
            logger.error("Failed to start directory watching", error=str(e))
            self.observer = None

    def stop_watching(self) -> None:
        """Stop watching directory."""
        if self.observer is not None:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("Directory watching stopped")

    def get_next_packet(self) -> Optional[MscPacket]:
        """
        Get next packet for transmission using priority-based scheduling.

        Priority scheduling algorithm:
        1. Start with highest priority (8)
        2. Transmit one packet from one object at current priority
        3. Move to next object in priority queue (round-robin)
        4. When priority queue exhausted, move to next lower priority
        5. When all priorities exhausted, wrap to highest priority

        Returns:
            Next packet to transmit, or None if carousel empty
        """
        if not self.objects:
            return None

        # Try up to 8 priorities
        attempts = 0
        while attempts < 8:
            # Get queue for current priority
            queue = self.priority_queues[self.current_priority]

            if queue:
                # Get transport_id from current position
                if self.current_index_in_priority >= len(queue):
                    self.current_index_in_priority = 0

                transport_id = queue[self.current_index_in_priority]
                state = self.states[transport_id]

                # Get next packet from this object
                if state.current_packet_index >= len(state.packets):
                    state.current_packet_index = 0

                packet = state.packets[state.current_packet_index]

                # Update state
                state.current_packet_index += 1
                state.total_transmissions += 1
                state.last_transmission_time = time.time()

                # Move to next object in queue
                self.current_index_in_priority += 1

                # If queue exhausted, move to next priority
                if self.current_index_in_priority >= len(queue):
                    self.current_index_in_priority = 0
                    self.current_priority -= 1
                    if self.current_priority < 1:
                        self.current_priority = 8

                return packet

            # Queue empty, try next priority
            self.current_priority -= 1
            if self.current_priority < 1:
                self.current_priority = 8

            self.current_index_in_priority = 0
            attempts += 1

        # No packets available
        return None

    def get_statistics(self) -> Dict:
        """
        Get carousel statistics.

        Returns:
            Dictionary with carousel statistics
        """
        total_packets = sum(len(state.packets) for state in self.states.values())
        total_transmissions = sum(
            state.total_transmissions for state in self.states.values()
        )

        # Per-object statistics
        object_stats = []
        for transport_id, obj in self.objects.items():
            state = self.states[transport_id]
            object_stats.append({
                'transport_id': transport_id,
                'priority': obj.priority,
                'enabled': obj.enabled,
                'packets': len(state.packets),
                'transmissions': state.total_transmissions,
                'last_transmission': state.last_transmission_time
            })

        # Priority distribution
        priority_dist = {
            p: len(queue) for p, queue in self.priority_queues.items()
        }

        return {
            'directory': str(self.directory),
            'watching': self.observer is not None,
            'total_objects': len(self.objects),
            'total_packets': total_packets,
            'total_transmissions': total_transmissions,
            'priority_distribution': priority_dist,
            'objects': object_stats
        }

    def __del__(self):
        """Cleanup on deletion."""
        self.stop_watching()
