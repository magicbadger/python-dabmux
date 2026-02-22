"""
Stress Testing Suite.

Tests multiplexer behavior under stress conditions:
- Maximum services (64)
- Maximum subchannels (64)
- Long-running frame generation
- Memory stability
- Rapid configuration changes
"""
import pytest
import psutil
import os
from dabmux.core.mux_elements import (
    DabEnsemble, DabService, DabSubchannel, DabComponent,
    DabLabel, ProtectionLevel, SubchannelType, TransmissionMode
)
from dabmux.mux import DabMultiplexer
from dabmux.fig.fic import FICEncoder


class TestMaximumServices:
    """Test multiplexer with maximum number of services."""

    def test_32_services(self):
        """Create ensemble with 32 services."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='32 Services'),
            transmission_mode=TransmissionMode.I
        )

        # Add 32 subchannels (one per service)
        for i in range(32):
            subchannel = DabSubchannel(
                uid=f'audio{i}',
                id=i,
                type=SubchannelType.DABPLUS,
                bitrate=24,  # Low bitrate to fit all
                protection=ProtectionLevel.EEP_3A,
                input_uri=f'file:///audio{i}.dabp'
            )
            ensemble.subchannels.append(subchannel)

        # Add 32 services
        for i in range(32):
            service = DabService(
                uid=f'service{i}',
                id=0x5001 + i,
                label=DabLabel(text=f'Service {i:02d}'),
                pty=10,
                language=9
            )
            ensemble.services.append(service)

        # Add 32 components
        for i in range(32):
            component = DabComponent(
                uid=f'component{i}',
                service_id=0x5001 + i,
                subchannel_id=i
            )
            ensemble.components.append(component)

        # Create multiplexer
        mux = DabMultiplexer(ensemble)

        # Generate frames
        frames_generated = 0
        for _ in range(100):
            frame = mux.generate_frame()
            assert frame is not None
            frames_generated += 1

        assert frames_generated == 100

    def test_64_services(self):
        """Create ensemble with 64 services (maximum)."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='64 Services'),
            transmission_mode=TransmissionMode.I
        )

        # Add 64 subchannels with minimum bitrate
        for i in range(64):
            subchannel = DabSubchannel(
                uid=f'audio{i}',
                id=i,
                type=SubchannelType.DABPLUS,
                bitrate=8,  # Minimum bitrate
                protection=ProtectionLevel.EEP_4A,  # Low protection for capacity
                input_uri=f'file:///audio{i}.dabp'
            )
            ensemble.subchannels.append(subchannel)

        # Add 64 services
        for i in range(64):
            service = DabService(
                uid=f'service{i}',
                id=0x5001 + i,
                label=DabLabel(text=f'Svc {i:02d}'),
                pty=10,
                language=9
            )
            ensemble.services.append(service)

        # Add 64 components
        for i in range(64):
            component = DabComponent(
                uid=f'component{i}',
                service_id=0x5001 + i,
                subchannel_id=i
            )
            ensemble.components.append(component)

        # Create multiplexer
        mux = DabMultiplexer(ensemble)

        # Generate frames
        frames_generated = 0
        for _ in range(100):
            frame = mux.generate_frame()
            assert frame is not None
            frames_generated += 1

        assert frames_generated == 100

    def test_fic_with_many_services(self):
        """Verify FIC handling with many services."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='Many Services'),
            transmission_mode=TransmissionMode.I
        )

        # Add 32 services
        for i in range(32):
            service = DabService(
                uid=f'service{i}',
                id=0x5001 + i,
                label=DabLabel(text=f'Service {i:02d}'),
                pty=10,
                language=9
            )
            ensemble.services.append(service)

        # Create FIC encoder
        fic = FICEncoder(ensemble)

        # Generate FIC data multiple times
        for _ in range(10):
            fic_data = fic.generate_fic()
            assert len(fic_data) == 96  # 3 FIBs × 32 bytes


class TestMaximumSubchannels:
    """Test multiplexer with maximum number of subchannels."""

    def test_64_subchannels(self):
        """Create ensemble with 64 subchannels (maximum)."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='64 Subchannels'),
            transmission_mode=TransmissionMode.I
        )

        # Add 64 subchannels
        for i in range(64):
            subchannel = DabSubchannel(
                uid=f'sub{i}',
                id=i,
                type=SubchannelType.DABPLUS,
                bitrate=8,
                protection=ProtectionLevel.EEP_4A,
                input_uri=f'file:///sub{i}.dabp'
            )
            ensemble.subchannels.append(subchannel)

        # Create multiplexer
        mux = DabMultiplexer(ensemble)

        # Generate frame
        frame = mux.generate_frame()
        assert frame is not None


class TestMemoryStability:
    """Test memory usage and stability over time."""

    def test_10000_frames_memory(self):
        """Generate 10,000 frames and monitor memory."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='Memory Test'),
            transmission_mode=TransmissionMode.I
        )

        # Add 8 services (typical ensemble)
        for i in range(8):
            subchannel = DabSubchannel(
                uid=f'audio{i}',
                id=i,
                type=SubchannelType.DABPLUS,
                bitrate=48,
                protection=ProtectionLevel.EEP_3A,
                input_uri=f'file:///audio{i}.dabp'
            )
            ensemble.subchannels.append(subchannel)

            service = DabService(
                uid=f'service{i}',
                id=0x5001 + i,
                label=DabLabel(text=f'Service {i}'),
                pty=10,
                language=9
            )
            ensemble.services.append(service)

            component = DabComponent(
                uid=f'component{i}',
                service_id=0x5001 + i,
                subchannel_id=i
            )
            ensemble.components.append(component)

        # Create multiplexer
        mux = DabMultiplexer(ensemble)

        # Get process for memory monitoring
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Generate 10,000 frames
        for _ in range(10000):
            frame = mux.generate_frame()
            assert frame is not None

        # Check final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Memory should not grow significantly (< 100 MB increase)
        memory_growth = final_memory - initial_memory
        assert memory_growth < 100, f"Memory grew by {memory_growth:.2f} MB"

    def test_frame_generation_speed(self):
        """Measure frame generation speed."""
        import time

        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='Speed Test'),
            transmission_mode=TransmissionMode.I
        )

        # Add typical 4-service ensemble
        for i in range(4):
            subchannel = DabSubchannel(
                uid=f'audio{i}',
                id=i,
                type=SubchannelType.DABPLUS,
                bitrate=64,
                protection=ProtectionLevel.EEP_3A,
                input_uri=f'file:///audio{i}.dabp'
            )
            ensemble.subchannels.append(subchannel)

            service = DabService(
                uid=f'service{i}',
                id=0x5001 + i,
                label=DabLabel(text=f'Service {i}'),
                pty=10,
                language=9
            )
            ensemble.services.append(service)

            component = DabComponent(
                uid=f'component{i}',
                service_id=0x5001 + i,
                subchannel_id=i
            )
            ensemble.components.append(component)

        mux = DabMultiplexer(ensemble)

        # Generate 1000 frames and measure time
        start_time = time.time()
        for _ in range(1000):
            frame = mux.generate_frame()
            assert frame is not None
        elapsed = time.time() - start_time

        # Calculate frames per second
        fps = 1000 / elapsed

        # DAB Mode I requires 40 frames/second (24ms per frame)
        # We should be able to generate >> 40 fps
        assert fps > 100, f"Only {fps:.1f} fps (need > 100)"


class TestRapidConfigurationChanges:
    """Test rapid configuration changes."""

    def test_add_remove_services(self):
        """Add and remove services repeatedly."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='Dynamic Config'),
            transmission_mode=TransmissionMode.I
        )

        mux = DabMultiplexer(ensemble)

        # Perform 10 cycles of add/remove
        for cycle in range(10):
            # Add 8 services
            for i in range(8):
                subchannel = DabSubchannel(
                    uid=f'sub{cycle}_{i}',
                    id=i,
                    type=SubchannelType.DABPLUS,
                    bitrate=48,
                    protection=ProtectionLevel.EEP_3A,
                    input_uri=f'file:///audio{i}.dabp'
                )
                ensemble.subchannels.append(subchannel)

                service = DabService(
                    uid=f'svc{cycle}_{i}',
                    id=0x5001 + i,
                    label=DabLabel(text=f'Svc{i}'),
                    pty=10,
                    language=9
                )
                ensemble.services.append(service)

                component = DabComponent(
                    uid=f'comp{cycle}_{i}',
                    service_id=0x5001 + i,
                    subchannel_id=i
                )
                ensemble.components.append(component)

            # Generate some frames
            for _ in range(10):
                frame = mux.generate_frame()
                assert frame is not None

            # Remove all services
            ensemble.subchannels.clear()
            ensemble.services.clear()
            ensemble.components.clear()

    def test_fig0_7_counter_updates(self):
        """Verify FIG 0/7 configuration counter updates."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='Config Counter'),
            transmission_mode=TransmissionMode.I
        )

        # Get initial configuration hash
        hash1 = ensemble.calculate_configuration_hash()

        # Add a subchannel
        subchannel = DabSubchannel(
            uid='audio1',
            id=0,
            type=SubchannelType.DABPLUS,
            bitrate=48,
            protection=ProtectionLevel.EEP_3A,
            input_uri='file:///audio1.dabp'
        )
        ensemble.subchannels.append(subchannel)

        # Get new configuration hash
        hash2 = ensemble.calculate_configuration_hash()

        # Hash should change
        assert hash1 != hash2

        # Add another subchannel
        subchannel2 = DabSubchannel(
            uid='audio2',
            id=1,
            type=SubchannelType.DABPLUS,
            bitrate=64,
            protection=ProtectionLevel.EEP_3A,
            input_uri='file:///audio2.dabp'
        )
        ensemble.subchannels.append(subchannel2)

        # Get another hash
        hash3 = ensemble.calculate_configuration_hash()

        # Hash should change again
        assert hash2 != hash3


class TestBoundaryConditions:
    """Test boundary conditions and limits."""

    def test_minimum_bitrate(self):
        """Test with minimum bitrate (8 kbps)."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='Min Bitrate'),
            transmission_mode=TransmissionMode.I
        )

        subchannel = DabSubchannel(
            uid='min_audio',
            id=0,
            type=SubchannelType.DABPLUS,
            bitrate=8,  # Minimum
            protection=ProtectionLevel.EEP_4A,
            input_uri='file:///audio.dabp'
        )
        ensemble.subchannels.append(subchannel)

        mux = DabMultiplexer(ensemble)
        frame = mux.generate_frame()
        assert frame is not None

    def test_maximum_bitrate(self):
        """Test with high bitrate (192 kbps)."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='Max Bitrate'),
            transmission_mode=TransmissionMode.I
        )

        subchannel = DabSubchannel(
            uid='max_audio',
            id=0,
            type=SubchannelType.DABPLUS,
            bitrate=192,  # High bitrate
            protection=ProtectionLevel.EEP_1A,
            input_uri='file:///audio.dabp'
        )
        ensemble.subchannels.append(subchannel)

        mux = DabMultiplexer(ensemble)
        frame = mux.generate_frame()
        assert frame is not None

    def test_empty_ensemble_stability(self):
        """Test with empty ensemble (no services)."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='Empty'),
            transmission_mode=TransmissionMode.I
        )

        mux = DabMultiplexer(ensemble)

        # Generate 100 frames with no services
        for _ in range(100):
            frame = mux.generate_frame()
            assert frame is not None


class TestConcurrentOperations:
    """Test concurrent operations (if applicable)."""

    def test_multiple_fic_encoders(self):
        """Create multiple FIC encoders for same ensemble."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='Multi FIC'),
            transmission_mode=TransmissionMode.I
        )

        # Add some services
        for i in range(4):
            service = DabService(
                uid=f'service{i}',
                id=0x5001 + i,
                label=DabLabel(text=f'Service {i}'),
                pty=10,
                language=9
            )
            ensemble.services.append(service)

        # Create multiple FIC encoders
        fic1 = FICEncoder(ensemble)
        fic2 = FICEncoder(ensemble)
        fic3 = FICEncoder(ensemble)

        # Generate FIC data from all
        data1 = fic1.generate_fic()
        data2 = fic2.generate_fic()
        data3 = fic3.generate_fic()

        # All should be valid
        assert len(data1) == 96
        assert len(data2) == 96
        assert len(data3) == 96


# Pytest collection
__all__ = [
    'TestMaximumServices',
    'TestMaximumSubchannels',
    'TestMemoryStability',
    'TestRapidConfigurationChanges',
    'TestBoundaryConditions',
    'TestConcurrentOperations',
]
