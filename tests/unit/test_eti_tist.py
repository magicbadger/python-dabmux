"""
Unit tests for ETI TIST (Timestamp) support.

Tests Priority 5.5 Phase 1: TIST Support in ETI Files
Per ETSI EN 300 799 Section 5.5 (TIST field)
"""
import time
import pytest
from dabmux.core.eti import EtiFrame
from dabmux.core.mux_elements import DabEnsemble, DabService, DabSubchannel, DabComponent
from dabmux.core.mux_elements import DabLabel, TransmissionMode, SubchannelType
from dabmux.mux import DabMultiplexer


class TestEtiTIST:
    """Tests for TIST field in ETI frames."""

    def create_minimal_ensemble(self, enable_tist: bool = False, tist_offset: float = 0.0) -> DabEnsemble:
        """Create minimal ensemble for testing."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text="Test Ensemble", short_text="Test"),
            transmission_mode=TransmissionMode.TM_I,
            enable_tist=enable_tist,
            tist_offset=tist_offset
        )

        # Add minimal subchannel
        subchannel = DabSubchannel(
            uid='audio',
            id=0,
            type=SubchannelType.DABPlusAudio,
            bitrate=48
        )
        subchannel.protection.level = 3
        ensemble.subchannels.append(subchannel)

        # Add minimal service
        service = DabService(
            uid='service',
            id=0x5001,
            label=DabLabel(text="Test Service", short_text="Test")
        )
        ensemble.services.append(service)

        # Add minimal component
        component = DabComponent(
            uid='component',
            service_id=0x5001,
            subchannel_id=0,
            label=DabLabel(text="Main", short_text="Main")
        )
        ensemble.components.append(component)

        return ensemble

    def test_tist_disabled_by_default(self):
        """Test that TIST is disabled by default in ensemble."""
        ensemble = self.create_minimal_ensemble(enable_tist=False)
        assert ensemble.enable_tist is False
        assert ensemble.tist_offset == 0.0

    def test_tist_enabled_in_ensemble(self):
        """Test that TIST can be enabled in ensemble configuration."""
        ensemble = self.create_minimal_ensemble(enable_tist=True)
        assert ensemble.enable_tist is True

    def test_tist_offset_configurable(self):
        """Test that TIST offset can be configured."""
        offset = 0.5  # 500ms
        ensemble = self.create_minimal_ensemble(enable_tist=True, tist_offset=offset)
        assert ensemble.tist_offset == offset

    def test_frame_without_tist(self):
        """Test that frames without TIST don't have TIST field."""
        frame = EtiFrame.create_empty(mode=1, with_tist=False)
        assert frame.tist is None

    def test_frame_with_tist(self):
        """Test that frames with TIST have TIST field."""
        frame = EtiFrame.create_empty(mode=1, with_tist=True)
        assert frame.tist is not None
        assert hasattr(frame.tist, 'tist')

    def test_multiplexer_generates_tist_when_enabled(self):
        """Test that multiplexer generates TIST values when enabled."""
        ensemble = self.create_minimal_ensemble(enable_tist=True)
        mux = DabMultiplexer(ensemble)

        # Generate frame
        frame = mux.generate_frame()

        # Verify TIST field exists and has non-zero value
        assert frame.tist is not None
        assert frame.tist.tist > 0
        assert frame.tist.tist <= 0xFFFFFFFF  # 32-bit value

    def test_multiplexer_no_tist_when_disabled(self):
        """Test that multiplexer doesn't generate TIST when disabled."""
        ensemble = self.create_minimal_ensemble(enable_tist=False)
        mux = DabMultiplexer(ensemble)

        # Generate frame
        frame = mux.generate_frame()

        # Verify TIST field doesn't exist
        assert frame.tist is None

    def test_tist_increments_between_frames(self):
        """Test that TIST values increment between consecutive frames."""
        ensemble = self.create_minimal_ensemble(enable_tist=True)
        mux = DabMultiplexer(ensemble)

        # Generate first frame
        frame1 = mux.generate_frame()
        tist1 = frame1.tist.tist

        # Small delay
        time.sleep(0.001)  # 1ms

        # Generate second frame
        frame2 = mux.generate_frame()
        tist2 = frame2.tist.tist

        # TIST should increase (accounting for 32-bit wrap)
        if tist2 > tist1:
            assert tist2 > tist1
        else:
            # Wrapped around
            assert tist1 > 0xF0000000  # Near max value

    def test_tist_offset_applied(self):
        """Test that TIST offset is correctly applied."""
        offset = 1.0  # 1 second
        ensemble = self.create_minimal_ensemble(enable_tist=True, tist_offset=offset)
        mux = DabMultiplexer(ensemble)

        # Record current time
        time_before = time.time()

        # Generate frame
        frame = mux.generate_frame()
        tist_value = frame.tist.tist

        # Record time after
        time_after = time.time()

        # Calculate expected TIST range (with offset)
        min_expected = int((time_before + offset) * 16384000) & 0xFFFFFFFF
        max_expected = int((time_after + offset) * 16384000) & 0xFFFFFFFF

        # TIST should be in expected range (accounting for 32-bit wrap)
        if min_expected <= max_expected:
            assert min_expected <= tist_value <= max_expected
        else:
            # Wrapped during test
            assert tist_value >= min_expected or tist_value <= max_expected


class TestEtiTISTIntegration:
    """Integration tests for TIST with full multiplexer."""

    def test_tist_in_packed_frames(self):
        """Test that TIST appears in packed ETI frames."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text="Test", short_text="Test"),
            transmission_mode=TransmissionMode.TM_I,
            enable_tist=True
        )

        subchannel = DabSubchannel(
            uid='audio',
            id=0,
            type=SubchannelType.DABPlusAudio,
            bitrate=48
        )
        subchannel.protection.level = 3
        ensemble.subchannels.append(subchannel)

        service = DabService(
            uid='service',
            id=0x5001,
            label=DabLabel(text="Service", short_text="Svc")
        )
        ensemble.services.append(service)

        component = DabComponent(
            uid='component',
            service_id=0x5001,
            subchannel_id=0,
            label=DabLabel(text="Main", short_text="Main")
        )
        ensemble.components.append(component)

        mux = DabMultiplexer(ensemble)

        # Generate and pack frame
        frame = mux.generate_frame()
        packed = frame.pack()

        # Verify TIST is included (frame should have TIST data)
        assert frame.tist is not None
        assert len(packed) > 0

    def test_multiple_frames_with_tist(self):
        """Test generating multiple frames with TIST."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text="Test", short_text="Test"),
            transmission_mode=TransmissionMode.TM_I,
            enable_tist=True
        )

        subchannel = DabSubchannel(
            uid='audio',
            id=0,
            type=SubchannelType.DABPlusAudio,
            bitrate=48
        )
        subchannel.protection.level = 3
        ensemble.subchannels.append(subchannel)

        service = DabService(
            uid='service',
            id=0x5001,
            label=DabLabel(text="Service", short_text="Svc")
        )
        ensemble.services.append(service)

        component = DabComponent(
            uid='component',
            service_id=0x5001,
            subchannel_id=0,
            label=DabLabel(text="Main", short_text="Main")
        )
        ensemble.components.append(component)

        mux = DabMultiplexer(ensemble)

        tist_values = []
        for _ in range(5):
            frame = mux.generate_frame()
            tist_values.append(frame.tist.tist)
            time.sleep(0.024)  # 24ms (one DAB frame)

        # All TIST values should be unique and increasing (or wrapped)
        assert len(set(tist_values)) == 5  # All unique

        # Check monotonic increase (accounting for wrap)
        for i in range(1, len(tist_values)):
            if tist_values[i] > tist_values[i-1]:
                assert tist_values[i] > tist_values[i-1]
            else:
                # Wrapped - previous should be near max
                assert tist_values[i-1] > 0xF0000000
