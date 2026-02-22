"""
Unit tests for FIG 0/13 (User Application Information).

Tests MOT signaling per ETSI EN 300 401 Section 8.1.20.
"""

import pytest
from dabmux.fig.fig0 import FIG0_13
from dabmux.core.mux_elements import DabEnsemble, DabService, DabSubchannel, DabComponent


class TestFIG0_13:
    """Tests for FIG 0/13 (User Application Information)."""

    def create_test_ensemble_with_mot(self):
        """Create test ensemble with MOT carousel enabled."""
        ensemble = DabEnsemble()
        ensemble.id = 0xCE15
        ensemble.ecc = 0xE1

        # Service
        service = DabService(uid='radio1')
        service.id = 0x5001
        ensemble.services.append(service)

        # Subchannel (packet mode for MOT)
        subchannel = DabSubchannel(uid='data_ch')
        subchannel.id = 1
        subchannel.type = 'packet'
        ensemble.subchannels.append(subchannel)

        # Component with MOT carousel
        component = DabComponent(uid='mot_comp')
        component.service_id = service.id
        component.subchannel_id = subchannel.id
        component.is_packet_mode = True
        component.carousel_enabled = True
        component.carousel_directory = '/carousel'
        ensemble.components.append(component)

        return ensemble

    def test_fig0_13_creation(self):
        """Test creating FIG 0/13."""
        ensemble = self.create_test_ensemble_with_mot()
        fig = FIG0_13(ensemble)

        assert fig.ensemble == ensemble
        assert fig.fig_type() == 0
        assert fig.fig_extension() == 13

    def test_fig0_13_no_mot_components(self):
        """Test FIG 0/13 with no MOT components."""
        ensemble = DabEnsemble()
        fig = FIG0_13(ensemble)

        buf = bytearray(256)
        status = fig.fill(buf, 256)

        # Should return empty (no MOT components)
        assert status.num_bytes_written == 0
        assert status.complete_fig_transmitted is True

    def test_fig0_13_with_mot_component(self):
        """Test FIG 0/13 with MOT component."""
        ensemble = self.create_test_ensemble_with_mot()
        fig = FIG0_13(ensemble)

        buf = bytearray(256)
        status = fig.fill(buf, 256)

        # Should encode MOT signaling
        assert status.num_bytes_written > 0

        # Check Service ID (16-bit)
        sid = (buf[0] << 8) | buf[1]
        assert sid == 0x5001

        # Check SCIdS (4 bits) + No (4 bits)
        scids_no = buf[2]
        scids = (scids_no >> 4) & 0x0F
        no = scids_no & 0x0F
        assert no == 1  # One user application

        # Check UA Type (MOT Slideshow = 0x002)
        ua_type_high = (buf[3] >> 5) & 0x07
        ua_type_low = buf[4]
        ua_type = (ua_type_high << 8) | ua_type_low
        assert ua_type == 0x002  # MOT Slideshow

    def test_fig0_13_32bit_sid(self):
        """Test FIG 0/13 with 32-bit Service ID."""
        ensemble = self.create_test_ensemble_with_mot()

        # Use 32-bit service ID
        ensemble.services[0].id = 0x12345678
        ensemble.components[0].service_id = 0x12345678  # Update component too

        fig = FIG0_13(ensemble)

        buf = bytearray(256)
        status = fig.fill(buf, 256)

        # Should encode with 32-bit SId
        assert status.num_bytes_written > 6  # At least 4 bytes for SId + data

        # Check 32-bit Service ID
        sid = (buf[0] << 24) | (buf[1] << 16) | (buf[2] << 8) | buf[3]
        assert sid == 0x12345678

    def test_fig0_13_multiple_mot_components(self):
        """Test FIG 0/13 with multiple MOT components."""
        ensemble = DabEnsemble()

        # Service 1
        service1 = DabService(uid='radio1')
        service1.id = 0x5001
        ensemble.services.append(service1)

        subchannel1 = DabSubchannel(uid='data_ch1')
        subchannel1.id = 1
        subchannel1.type = 'packet'
        ensemble.subchannels.append(subchannel1)

        component1 = DabComponent(uid='mot_comp1')
        component1.service_id = service1.id
        component1.subchannel_id = subchannel1.id
        component1.is_packet_mode = True
        component1.carousel_enabled = True
        ensemble.components.append(component1)

        # Service 2
        service2 = DabService(uid='radio2')
        service2.id = 0x5002
        ensemble.services.append(service2)

        subchannel2 = DabSubchannel(uid='data_ch2')
        subchannel2.id = 2
        subchannel2.type = 'packet'
        ensemble.subchannels.append(subchannel2)

        component2 = DabComponent(uid='mot_comp2')
        component2.service_id = service2.id
        component2.subchannel_id = subchannel2.id
        component2.is_packet_mode = True
        component2.carousel_enabled = True
        ensemble.components.append(component2)

        fig = FIG0_13(ensemble)

        buf = bytearray(256)
        status = fig.fill(buf, 256)

        # Should encode both components
        assert status.num_bytes_written >= 14  # At least 7 bytes per component

    def test_fig0_13_disabled_carousel(self):
        """Test FIG 0/13 skips disabled carousel."""
        ensemble = self.create_test_ensemble_with_mot()

        # Disable carousel
        ensemble.components[0].carousel_enabled = False

        fig = FIG0_13(ensemble)

        buf = bytearray(256)
        status = fig.fill(buf, 256)

        # Should return empty (carousel disabled)
        assert status.num_bytes_written == 0

    def test_fig0_13_buffer_too_small(self):
        """Test FIG 0/13 with insufficient buffer."""
        ensemble = self.create_test_ensemble_with_mot()
        fig = FIG0_13(ensemble)

        buf = bytearray(256)
        status = fig.fill(buf, 5)  # Too small

        # Should not write anything
        assert status.num_bytes_written == 0

    def test_fig0_13_ua_data_length(self):
        """Test FIG 0/13 UA data length field."""
        ensemble = self.create_test_ensemble_with_mot()
        fig = FIG0_13(ensemble)

        buf = bytearray(256)
        status = fig.fill(buf, 256)

        # Check UA Data Length (5 bits in byte 5, top 5 bits)
        ua_data_length = (buf[5] >> 3) & 0x1F
        assert ua_data_length == 1  # 1 byte for transport mechanism

        # Check UA Data (transport mechanism = 0x00 for packet mode)
        assert buf[6] == 0x00

    def test_fig0_13_repetition_rate(self):
        """Test FIG 0/13 repetition rate."""
        ensemble = self.create_test_ensemble_with_mot()
        fig = FIG0_13(ensemble)

        from dabmux.fig.base import FIGRate

        assert fig.repetition_rate() == FIGRate.C  # Once every 3 seconds

    def test_fig0_13_scids_calculation(self):
        """Test SCIdS calculation for multiple components in same service."""
        ensemble = DabEnsemble()

        service = DabService(uid='radio1')
        service.id = 0x5001
        ensemble.services.append(service)

        # Add two components to same service
        for i in range(2):
            subchannel = DabSubchannel(uid=f'data_ch{i}')
            subchannel.id = i
            subchannel.type = 'packet'
            ensemble.subchannels.append(subchannel)

            component = DabComponent(uid=f'mot_comp{i}')
            component.service_id = service.id
            component.subchannel_id = subchannel.id
            component.is_packet_mode = True
            component.carousel_enabled = True
            ensemble.components.append(component)

        fig = FIG0_13(ensemble)

        buf = bytearray(256)
        status = fig.fill(buf, 256)

        # First component should have SCIdS=0
        scids_no_1 = buf[2]
        scids_1 = (scids_no_1 >> 4) & 0x0F
        assert scids_1 == 0

        # Second component should have SCIdS=1
        # Find offset to second component (after first component's data)
        # First component: SId(2) + SCIdS/No(1) + UA entry(3) + UA data(1) = 7 bytes
        # Second component starts at byte 7, SCIdS/No at byte 9 (after SId)
        scids_no_2 = buf[9]
        scids_2 = (scids_no_2 >> 4) & 0x0F
        assert scids_2 == 1
