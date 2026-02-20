"""
Unit tests for FIG 0/21 (Frequency Information).
"""
import pytest
import struct
from dabmux.core.mux_elements import (
    DabEnsemble, DabService, DabLabel,
    FrequencyEntry, FrequencyList
)
from dabmux.fig.fig0 import FIG0_21


class TestFIG0_21:
    """Test FIG 0/21 (Frequency Information) implementation."""

    def test_fig0_21_single_frequency(self):
        """Test FIG 0/21 encoding with single frequency."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)

        # Create service with one frequency list
        service = DabService(
            uid='test_svc',
            id=0x5001,
            label=DabLabel(text="Test")
        )

        freq_list = FrequencyList(
            list_id=0,
            continuity=1,
            r_flag=True
        )
        freq_entry = FrequencyEntry(
            frequency_mhz=225.648,
            freq_type='dab'
        )
        freq_list.frequencies.append(freq_entry)
        service.frequency_lists.append(freq_list)
        ensemble.services.append(service)

        fig = FIG0_21(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Verify status
        assert status.complete_fig_transmitted is True
        assert status.num_bytes_written == 8  # 2 header + 6 data

        # Verify header
        assert (buf[0] >> 5) == 0  # FIG type 0
        assert (buf[0] & 0x1F) == 7  # Length = 6 data + 1
        assert (buf[1] & 0x1F) == 21  # Extension 21

        # Verify data
        # Bytes 2-3: Service ID
        svc_id = struct.unpack('>H', buf[2:4])[0]
        assert svc_id == 0x5001

        # Byte 4: ListId (4 bits) + R flag + Continuity (2 bits)
        list_id = (buf[4] >> 4) & 0x0F
        r_flag = (buf[4] >> 3) & 0x01
        continuity = (buf[4] >> 1) & 0x03
        assert list_id == 0
        assert r_flag == 1
        assert continuity == 1

        # Byte 5: Length (number of frequencies)
        num_freqs = buf[5]
        assert num_freqs == 1

        # Bytes 6-7: Frequency (DAB encoding: MHz * 16)
        freq_encoded = struct.unpack('>H', buf[6:8])[0]
        expected_freq = int(225.648 * 16)
        assert freq_encoded == expected_freq

    def test_fig0_21_multiple_frequencies(self):
        """Test FIG 0/21 with multiple frequencies in one list."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)
        service = DabService(uid='test_svc', id=0x5001)

        freq_list = FrequencyList(list_id=0, continuity=0, r_flag=True)

        # Add multiple DAB frequencies
        for freq_mhz in [225.648, 226.352, 227.360]:
            freq_entry = FrequencyEntry(frequency_mhz=freq_mhz, freq_type='dab')
            freq_list.frequencies.append(freq_entry)

        service.frequency_lists.append(freq_list)
        ensemble.services.append(service)

        fig = FIG0_21(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Verify number of frequencies
        num_freqs = buf[5]
        assert num_freqs == 3

        # Verify all frequencies
        for i, expected_mhz in enumerate([225.648, 226.352, 227.360]):
            freq_encoded = struct.unpack('>H', buf[6 + i*2:8 + i*2])[0]
            expected = int(expected_mhz * 16)
            assert freq_encoded == expected

    def test_fig0_21_dab_frequency_encoding(self):
        """Test FIG 0/21 DAB frequency encoding."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)
        service = DabService(uid='test_svc', id=0x5001)

        freq_list = FrequencyList()
        freq_entry = FrequencyEntry(frequency_mhz=225.648, freq_type='dab')
        freq_list.frequencies.append(freq_entry)
        service.frequency_lists.append(freq_list)
        ensemble.services.append(service)

        fig = FIG0_21(ensemble)
        buf = bytearray(32)
        fig.fill(buf, 32)

        # Verify DAB encoding: MHz * 16
        freq_encoded = struct.unpack('>H', buf[6:8])[0]
        expected = int(225.648 * 16)  # 3610
        assert freq_encoded == expected

    def test_fig0_21_fm_frequency_encoding(self):
        """Test FIG 0/21 FM frequency encoding."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)
        service = DabService(uid='test_svc', id=0x5001)

        freq_list = FrequencyList()
        freq_entry = FrequencyEntry(frequency_mhz=101.5, freq_type='fm')
        freq_list.frequencies.append(freq_entry)
        service.frequency_lists.append(freq_list)
        ensemble.services.append(service)

        fig = FIG0_21(ensemble)
        buf = bytearray(32)
        fig.fill(buf, 32)

        # Verify FM encoding: (MHz - 87.5) * 200
        freq_encoded = struct.unpack('>H', buf[6:8])[0]
        expected = int((101.5 - 87.5) * 200)  # 2800
        assert freq_encoded == expected

    def test_fig0_21_mixed_dab_fm_frequencies(self):
        """Test FIG 0/21 with mixed DAB and FM frequencies."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)
        service = DabService(uid='test_svc', id=0x5001)

        freq_list = FrequencyList()

        # Add DAB frequency
        freq_list.frequencies.append(
            FrequencyEntry(frequency_mhz=225.648, freq_type='dab')
        )

        # Add FM frequency
        freq_list.frequencies.append(
            FrequencyEntry(frequency_mhz=101.5, freq_type='fm')
        )

        service.frequency_lists.append(freq_list)
        ensemble.services.append(service)

        fig = FIG0_21(ensemble)
        buf = bytearray(32)
        fig.fill(buf, 32)

        # Verify number of frequencies
        assert buf[5] == 2

        # Verify DAB encoding
        dab_freq = struct.unpack('>H', buf[6:8])[0]
        assert dab_freq == int(225.648 * 16)

        # Verify FM encoding
        fm_freq = struct.unpack('>H', buf[8:10])[0]
        assert fm_freq == int((101.5 - 87.5) * 200)

    def test_fig0_21_multiple_lists(self):
        """Test FIG 0/21 with multiple frequency lists per service."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)
        service = DabService(uid='test_svc', id=0x5001)

        # Add two frequency lists with different list IDs
        for list_id in [0, 1]:
            freq_list = FrequencyList(list_id=list_id, continuity=1)
            freq_list.frequencies.append(
                FrequencyEntry(frequency_mhz=225.648 + list_id, freq_type='dab')
            )
            service.frequency_lists.append(freq_list)

        ensemble.services.append(service)

        fig = FIG0_21(ensemble)

        # First call - should transmit first list (limit buffer to force split)
        buf1 = bytearray(32)
        status1 = fig.fill(buf1, 10)  # Small buffer, only fits one list
        assert status1.num_bytes_written > 0
        assert status1.complete_fig_transmitted is False

        list_id1 = (buf1[4] >> 4) & 0x0F

        # Second call - should transmit second list
        buf2 = bytearray(32)
        status2 = fig.fill(buf2, 32)
        assert status2.num_bytes_written > 0
        assert status2.complete_fig_transmitted is True

        list_id2 = (buf2[4] >> 4) & 0x0F

        # Verify different list IDs
        assert {list_id1, list_id2} == {0, 1}

    def test_fig0_21_list_id_field(self):
        """Test FIG 0/21 list ID field (0-15)."""
        # Test various list IDs
        for list_id in [0, 5, 10, 15]:
            ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)
            service = DabService(uid='test_svc', id=0x5001)

            freq_list = FrequencyList(list_id=list_id)
            freq_list.frequencies.append(
                FrequencyEntry(frequency_mhz=225.648, freq_type='dab')
            )
            service.frequency_lists.append(freq_list)
            ensemble.services.append(service)

            fig = FIG0_21(ensemble)
            buf = bytearray(32)
            fig.fill(buf, 32)

            # Verify list ID
            decoded_list_id = (buf[4] >> 4) & 0x0F
            assert decoded_list_id == list_id

    def test_fig0_21_r_flag(self):
        """Test FIG 0/21 R flag (list complete/incomplete)."""
        # Test R flag values
        for r_flag in [True, False]:
            ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)
            service = DabService(uid='test_svc', id=0x5001)

            freq_list = FrequencyList(r_flag=r_flag)
            freq_list.frequencies.append(
                FrequencyEntry(frequency_mhz=225.648, freq_type='dab')
            )
            service.frequency_lists.append(freq_list)
            ensemble.services.append(service)

            fig = FIG0_21(ensemble)
            buf = bytearray(32)
            fig.fill(buf, 32)

            # Verify R flag
            decoded_r_flag = (buf[4] >> 3) & 0x01
            assert decoded_r_flag == (1 if r_flag else 0)

    def test_fig0_21_continuity_flag(self):
        """Test FIG 0/21 continuity flag values (0-3)."""
        # Test all continuity values
        for continuity in [0, 1, 2, 3]:
            ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)
            service = DabService(uid='test_svc', id=0x5001)

            freq_list = FrequencyList(continuity=continuity)
            freq_list.frequencies.append(
                FrequencyEntry(frequency_mhz=225.648, freq_type='dab')
            )
            service.frequency_lists.append(freq_list)
            ensemble.services.append(service)

            fig = FIG0_21(ensemble)
            buf = bytearray(32)
            fig.fill(buf, 32)

            # Verify continuity
            decoded_continuity = (buf[4] >> 1) & 0x03
            assert decoded_continuity == continuity

    def test_fig0_21_iterative_transmission_services(self):
        """Test FIG 0/21 iterative transmission across services."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)

        # Add multiple services with frequency lists
        for svc_id in [0x5001, 0x5002]:
            service = DabService(uid=f'svc_{svc_id}', id=svc_id)
            freq_list = FrequencyList()
            freq_list.frequencies.append(
                FrequencyEntry(frequency_mhz=225.648, freq_type='dab')
            )
            service.frequency_lists.append(freq_list)
            ensemble.services.append(service)

        fig = FIG0_21(ensemble)
        transmitted_services = []

        # Transmit iteratively (limit buffer to force one service per call)
        for _ in range(2):
            buf = bytearray(32)
            status = fig.fill(buf, 10)  # Small buffer, only one service at a time
            if status.num_bytes_written > 0:
                # Extract service ID
                svc_id = struct.unpack('>H', buf[2:4])[0]
                transmitted_services.append(svc_id)

        # Should have transmitted both services
        assert set(transmitted_services) == {0x5001, 0x5002}

    def test_fig0_21_insufficient_space(self):
        """Test FIG 0/21 with insufficient buffer space."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)
        service = DabService(uid='test_svc', id=0x5001)

        freq_list = FrequencyList()
        freq_list.frequencies.append(
            FrequencyEntry(frequency_mhz=225.648, freq_type='dab')
        )
        service.frequency_lists.append(freq_list)
        ensemble.services.append(service)

        fig = FIG0_21(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 5)  # Only 5 bytes, need 8

        # Should not write anything
        assert status.num_bytes_written == 0
        assert status.complete_fig_transmitted is False

    def test_fig0_21_no_frequency_lists(self):
        """Test FIG 0/21 with no frequency lists (skip behavior)."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)
        service = DabService(uid='test_svc', id=0x5001)
        # No frequency lists
        ensemble.services.append(service)

        fig = FIG0_21(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Should not write anything
        assert status.num_bytes_written == 0
        assert status.complete_fig_transmitted is False

    def test_fig0_21_repetition_rate(self):
        """Test that FIG 0/21 has correct repetition rate."""
        ensemble = DabEnsemble(id=0xCE15)
        fig = FIG0_21(ensemble)

        from dabmux.fig.base import FIGRate
        assert fig.repetition_rate() == FIGRate.C

    def test_fig0_21_priority(self):
        """Test that FIG 0/21 has correct priority."""
        ensemble = DabEnsemble(id=0xCE15)
        fig = FIG0_21(ensemble)

        from dabmux.fig.base import FIGPriority
        assert fig.priority() == FIGPriority.NORMAL
