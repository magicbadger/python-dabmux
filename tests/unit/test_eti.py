"""
Unit tests for ETI frame structures.

These tests verify that ETI structures pack/unpack correctly and match
the binary layout of the C++ ODR-DabMux implementation.
"""
import pytest
from datetime import datetime
from dabmux.core.eti import (
    EtiSync, EtiFC, EtiSTC, EtiEOH, EtiEOF, EtiTIST,
    EtiMNSCTime0, EtiMNSCTime1, EtiMNSCTime2, EtiMNSCTime3,
    EtiFrame
)


class TestEtiSync:
    """Test ETI SYNC header."""

    def test_default_values(self) -> None:
        """Test default SYNC values."""
        sync = EtiSync()
        assert sync.err == 0xFF
        assert sync.fsync == 0x073AB6

    def test_pack_size(self) -> None:
        """SYNC should pack to exactly 4 bytes."""
        sync = EtiSync()
        data = sync.pack()
        assert len(data) == 4

    def test_pack_default(self) -> None:
        """Test packing with default values."""
        sync = EtiSync(err=0xFF, fsync=0x073AB6)
        data = sync.pack()
        # Big-endian per ETSI EN 300 799: ERR byte, then FSYNC (MSB first)
        assert data[0] == 0xFF  # ERR
        assert data[1] == 0x07  # FSYNC MSB
        assert data[2] == 0x3A  # FSYNC middle
        assert data[3] == 0xB6  # FSYNC LSB

    def test_pack_unpack_roundtrip(self) -> None:
        """Pack and unpack should be inverse operations."""
        sync = EtiSync(err=0xAA, fsync=0x073AB6)
        data = sync.pack()
        unpacked = EtiSync.unpack(data)
        assert unpacked.err == sync.err
        assert unpacked.fsync == sync.fsync

    def test_unpack_correct_values(self) -> None:
        """Test unpacking known byte sequence."""
        # Big-endian per ETSI EN 300 799: ERR byte, then FSYNC (MSB first)
        data = b'\xFF\x07\x3A\xB6'
        sync = EtiSync.unpack(data)
        assert sync.err == 0xFF
        assert sync.fsync == 0x073AB6


class TestEtiFC:
    """Test ETI Frame Characterization."""

    def test_default_values(self) -> None:
        """Test default FC values."""
        fc = EtiFC()
        assert fc.fct == 0
        assert fc.nst == 0
        assert fc.ficf == 1
        assert fc.mid == 1

    def test_pack_size(self) -> None:
        """FC should pack to exactly 4 bytes."""
        fc = EtiFC()
        data = fc.pack()
        assert len(data) == 4

    def test_frame_length_getter_setter(self) -> None:
        """Test frame length getter/setter."""
        fc = EtiFC()
        fc.set_frame_length(1000)
        assert fc.get_frame_length() == 1000
        assert fc.fl == 1000

    def test_frame_length_11bit_max(self) -> None:
        """Frame length should be limited to 11 bits (0-2047)."""
        fc = EtiFC()
        fc.set_frame_length(0xFFF)  # 12 bits
        assert fc.get_frame_length() == 0x7FF  # Masked to 11 bits

    def test_pack_unpack_roundtrip(self) -> None:
        """Pack and unpack should be inverse operations."""
        fc = EtiFC(fct=42, nst=5, ficf=1, mid=1, fp=3, fl=512)
        data = fc.pack()
        unpacked = EtiFC.unpack(data)
        assert unpacked.fct == fc.fct
        assert unpacked.nst == fc.nst
        assert unpacked.ficf == fc.ficf
        assert unpacked.mid == fc.mid
        assert unpacked.fp == fc.fp
        assert unpacked.fl == fc.fl

    def test_pack_empty_frame(self) -> None:
        """Test packing frame with no subchannels."""
        fc = EtiFC(fct=0, nst=0, ficf=1, mid=1, fp=0, fl=0)
        data = fc.pack()
        assert len(data) == 4


class TestEtiSTC:
    """Test ETI Sub-channel header."""

    def test_default_values(self) -> None:
        """Test default STC values."""
        stc = EtiSTC()
        assert stc.scid == 0
        assert stc.start_address == 0
        assert stc.tpl == 0
        assert stc.stl == 0

    def test_pack_size(self) -> None:
        """STC should pack to exactly 4 bytes."""
        stc = EtiSTC()
        data = stc.pack()
        assert len(data) == 4

    def test_stl_getter_setter(self) -> None:
        """Test STL getter/setter."""
        stc = EtiSTC()
        stc.set_stl(256)
        assert stc.get_stl() == 256
        assert stc.stl == 256

    def test_start_address_getter_setter(self) -> None:
        """Test start address getter/setter."""
        stc = EtiSTC()
        stc.set_start_address(100)
        assert stc.get_start_address() == 100
        assert stc.start_address == 100

    def test_10bit_fields(self) -> None:
        """Test that 10-bit fields are properly masked."""
        stc = EtiSTC()
        stc.set_stl(0xFFF)  # 12 bits
        assert stc.get_stl() == 0x3FF  # Masked to 10 bits

        stc.set_start_address(0xFFF)  # 12 bits
        assert stc.get_start_address() == 0x3FF  # Masked to 10 bits

    def test_pack_unpack_roundtrip(self) -> None:
        """Pack and unpack should be inverse operations."""
        stc = EtiSTC(scid=5, start_address=100, tpl=10, stl=256)
        data = stc.pack()
        unpacked = EtiSTC.unpack(data)
        assert unpacked.scid == stc.scid
        assert unpacked.start_address == stc.start_address
        assert unpacked.tpl == stc.tpl
        assert unpacked.stl == stc.stl


class TestEtiEOH:
    """Test ETI End of Header."""

    def test_default_values(self) -> None:
        """Test default EOH values."""
        eoh = EtiEOH()
        assert eoh.mnsc == 0
        assert eoh.crc == 0

    def test_pack_size(self) -> None:
        """EOH should pack to exactly 4 bytes."""
        eoh = EtiEOH()
        data = eoh.pack()
        assert len(data) == 4

    def test_pack_unpack_roundtrip(self) -> None:
        """Pack and unpack should be inverse operations."""
        eoh = EtiEOH(mnsc=0x1234, crc=0xABCD)
        data = eoh.pack()
        unpacked = EtiEOH.unpack(data)
        assert unpacked.mnsc == eoh.mnsc
        assert unpacked.crc == eoh.crc


class TestEtiEOF:
    """Test ETI End of Frame."""

    def test_default_values(self) -> None:
        """Test default EOF values."""
        eof = EtiEOF()
        assert eof.crc == 0
        assert eof.rfu == 0x0000

    def test_pack_size(self) -> None:
        """EOF should pack to exactly 4 bytes."""
        eof = EtiEOF()
        data = eof.pack()
        assert len(data) == 4

    def test_pack_unpack_roundtrip(self) -> None:
        """Pack and unpack should be inverse operations."""
        eof = EtiEOF(crc=0x1234, rfu=0xFFFF)
        data = eof.pack()
        unpacked = EtiEOF.unpack(data)
        assert unpacked.crc == eof.crc
        assert unpacked.rfu == eof.rfu


class TestEtiTIST:
    """Test ETI Timestamp."""

    def test_default_values(self) -> None:
        """Test default TIST values."""
        tist = EtiTIST()
        assert tist.tist == 0

    def test_pack_size(self) -> None:
        """TIST should pack to exactly 4 bytes."""
        tist = EtiTIST()
        data = tist.pack()
        assert len(data) == 4

    def test_pack_unpack_roundtrip(self) -> None:
        """Pack and unpack should be inverse operations."""
        tist = EtiTIST(tist=0x12345678)
        data = tist.pack()
        unpacked = EtiTIST.unpack(data)
        assert unpacked.tist == tist.tist


class TestEtiMNSCTime:
    """Test MNSC Time structures."""

    def test_mnsc_time0_pack_size(self) -> None:
        """MNSC Time 0 should pack to 2 bytes."""
        t0 = EtiMNSCTime0()
        data = t0.pack()
        assert len(data) == 2

    def test_mnsc_time1_pack_size(self) -> None:
        """MNSC Time 1 should pack to 2 bytes."""
        t1 = EtiMNSCTime1()
        data = t1.pack()
        assert len(data) == 2

    def test_mnsc_time1_set_from_time(self) -> None:
        """Test setting time from datetime (BCD encoding)."""
        t1 = EtiMNSCTime1()
        dt = datetime(2024, 1, 15, 14, 37, 45)
        t1.set_from_time(dt)

        assert t1.second_unit == 5  # 45 seconds -> unit=5
        assert t1.second_tens == 4  # 45 seconds -> tens=4
        assert t1.minute_unit == 7  # 37 minutes -> unit=7
        assert t1.minute_tens == 3  # 37 minutes -> tens=3

    def test_mnsc_time2_set_from_time(self) -> None:
        """Test setting date from datetime (BCD encoding)."""
        t2 = EtiMNSCTime2()
        dt = datetime(2024, 1, 15, 14, 37, 45)
        t2.set_from_time(dt)

        assert t2.hour_unit == 4  # 14 hours -> unit=4
        assert t2.hour_tens == 1  # 14 hours -> tens=1
        assert t2.day_unit == 5  # 15 days -> unit=5
        assert t2.day_tens == 1  # 15 days -> tens=1

    def test_mnsc_time3_set_from_time(self) -> None:
        """Test setting month/year from datetime (BCD encoding)."""
        t3 = EtiMNSCTime3()
        dt = datetime(2024, 1, 15, 14, 37, 45)
        t3.set_from_time(dt)

        assert t3.month_unit == 1  # January -> unit=1
        assert t3.month_tens == 0  # January -> tens=0
        assert t3.year_unit == 4  # 2024-2000=24 -> unit=4
        assert t3.year_tens == 2  # 2024-2000=24 -> tens=2


class TestEtiFrame:
    """Test complete ETI frame."""

    def test_create_empty_frame(self) -> None:
        """Test creating an empty frame."""
        frame = EtiFrame.create_empty()

        assert frame.sync.fsync == 0x073AB6
        assert frame.fc.nst == 0
        assert frame.fc.ficf == 1
        assert len(frame.stc_headers) == 0
        assert len(frame.fic_data) == 96
        assert len(frame.subchannel_data) == 0

    def test_create_empty_frame_with_tist(self) -> None:
        """Test creating empty frame with TIST."""
        frame = EtiFrame.create_empty(with_tist=True)
        assert frame.tist is not None
        assert frame.tist.tist == 0

    def test_create_empty_frame_without_tist(self) -> None:
        """Test creating empty frame without TIST."""
        frame = EtiFrame.create_empty(with_tist=False)
        assert frame.tist is None

    def test_pack_empty_frame(self) -> None:
        """Test packing an empty frame."""
        frame = EtiFrame.create_empty()
        data = frame.pack()

        # Calculate expected size:
        # SYNC(4) + FC(4) + EOH(4) + FIC(96) + EOF(4) = 112 bytes
        assert len(data) == 112

    def test_pack_empty_frame_with_tist(self) -> None:
        """Test packing empty frame with TIST."""
        frame = EtiFrame.create_empty(with_tist=True)
        data = frame.pack()

        # With TIST: 112 + 4 = 116 bytes
        assert len(data) == 116

    def test_frame_structure_order(self) -> None:
        """Test that frame components are in correct order."""
        frame = EtiFrame.create_empty()
        data = frame.pack()

        # Verify SYNC at start (big-endian per ETSI EN 300 799)
        assert data[0] == 0xFF  # ERR byte
        assert data[1:4] == b'\x07\x3A\xB6'  # FSYNC (MSB first)

        # Verify FC after SYNC
        # FCT should be 0 (byte 4)
        assert data[4] == 0x00

    def test_frame_with_transmission_modes(self) -> None:
        """Test creating frames with different transmission modes."""
        for mode in [1, 2, 3, 4]:
            frame = EtiFrame.create_empty(mode=mode)
            assert frame.fc.mid == mode
            data = frame.pack()
            assert len(data) == 112


class TestEtiFrameStructureSizes:
    """Test that all ETI structures have correct sizes."""

    def test_all_structures_correct_size(self) -> None:
        """Verify all ETI structures pack to expected sizes."""
        assert len(EtiSync().pack()) == 4
        assert len(EtiFC().pack()) == 4
        assert len(EtiSTC().pack()) == 4
        assert len(EtiEOH().pack()) == 4
        assert len(EtiEOF().pack()) == 4
        assert len(EtiTIST().pack()) == 4
        assert len(EtiMNSCTime0().pack()) == 2
        assert len(EtiMNSCTime1().pack()) == 2
        assert len(EtiMNSCTime2().pack()) == 2
        assert len(EtiMNSCTime3().pack()) == 2
