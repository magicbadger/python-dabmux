"""
ETI (Ensemble Transport Interface) frame structures.

This module provides the core data structures for building ETI frames,
matching the binary layout of the ODR-DabMux C++ implementation.
"""
import struct
from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class EtiSync:
    """
    ETI SYNC header (4 bytes).

    Layout (32 bits):
        ERR:    8 bits  - Error indicator
        FSYNC: 24 bits  - Frame sync word (constant 0x49C5F8)
    """
    err: int = 0xFF
    fsync: int = 0x49C5F8  # Constant sync word

    def pack(self) -> bytes:
        """Pack to 4 bytes (little-endian)."""
        # Combine: fsync (bits 8-31) | err (bits 0-7)
        value = (self.fsync << 8) | self.err
        return struct.pack('<I', value)

    @classmethod
    def unpack(cls, data: bytes) -> 'EtiSync':
        """Unpack from 4 bytes."""
        value = struct.unpack('<I', data[:4])[0]
        err = value & 0xFF
        fsync = (value >> 8) & 0xFFFFFF
        return cls(err=err, fsync=fsync)


@dataclass
class EtiFC:
    """
    Frame Characterization (4 bytes).

    Layout (32 bits):
        FCT:     8 bits  - Frame count (0-255)
        NST:     7 bits  - Number of subchannels (0-64)
        FICF:    1 bit   - FIC flag (always 1)
        FL_high: 3 bits  - Frame length high bits
        MID:     2 bits  - Transmission mode (1=Mode I)
        FP:      3 bits  - Frame phase (0-7)
        FL_low:  8 bits  - Frame length low bits
    """
    fct: int = 0
    nst: int = 0
    ficf: int = 1
    mid: int = 1  # Mode I
    fp: int = 0
    fl: int = 0  # Combined frame length (11 bits)

    def get_frame_length(self) -> int:
        """Get combined 11-bit frame length."""
        return self.fl

    def set_frame_length(self, length: int) -> None:
        """Set combined 11-bit frame length."""
        self.fl = length & 0x7FF

    def pack(self) -> bytes:
        """Pack to 4 bytes (little-endian)."""
        # Split FL into high and low
        fl_high = (self.fl >> 8) & 0x07
        fl_low = self.fl & 0xFF

        # Pack bitfields into 32 bits
        # Byte 0: FCT[7:0]
        # Byte 1: FICF[0] NST[6:0]
        # Byte 2: FP[2:0] MID[1:0] FL_high[2:0]
        # Byte 3: FL_low[7:0]
        byte0 = self.fct & 0xFF
        byte1 = ((self.ficf & 0x01) << 7) | (self.nst & 0x7F)
        byte2 = ((self.fp & 0x07) << 5) | ((self.mid & 0x03) << 3) | (fl_high & 0x07)
        byte3 = fl_low & 0xFF

        return struct.pack('<BBBB', byte0, byte1, byte2, byte3)

    @classmethod
    def unpack(cls, data: bytes) -> 'EtiFC':
        """Unpack from 4 bytes."""
        byte0, byte1, byte2, byte3 = struct.unpack('<BBBB', data[:4])

        fct = byte0
        nst = byte1 & 0x7F
        ficf = (byte1 >> 7) & 0x01
        fl_high = byte2 & 0x07
        mid = (byte2 >> 3) & 0x03
        fp = (byte2 >> 5) & 0x07
        fl_low = byte3
        fl = (fl_high << 8) | fl_low

        return cls(fct=fct, nst=nst, ficf=ficf, mid=mid, fp=fp, fl=fl)


@dataclass
class EtiSTC:
    """
    Sub-channel header (4 bytes).

    Layout (32 bits):
        startAddress_high: 2 bits  - Start address high bits
        SCID:              6 bits  - Subchannel ID
        startAddress_low:  8 bits  - Start address low bits
        STL_high:          2 bits  - Subchannel length high bits
        TPL:               6 bits  - Sub-channel protection level
        STL_low:           8 bits  - Subchannel length low bits
    """
    scid: int = 0
    start_address: int = 0  # Combined 10 bits
    tpl: int = 0
    stl: int = 0  # Combined 10 bits (Sub-channel stream length)

    def get_stl(self) -> int:
        """Get combined 10-bit subchannel length."""
        return self.stl

    def set_stl(self, length: int) -> None:
        """Set combined 10-bit subchannel length."""
        self.stl = length & 0x3FF

    def get_start_address(self) -> int:
        """Get combined 10-bit start address."""
        return self.start_address

    def set_start_address(self, address: int) -> None:
        """Set combined 10-bit start address."""
        self.start_address = address & 0x3FF

    def pack(self) -> bytes:
        """Pack to 4 bytes (little-endian)."""
        # Split combined fields
        start_addr_high = (self.start_address >> 8) & 0x03
        start_addr_low = self.start_address & 0xFF
        stl_high = (self.stl >> 8) & 0x03
        stl_low = self.stl & 0xFF

        # Byte 0: SCID[5:0] startAddress_high[1:0]
        # Byte 1: startAddress_low[7:0]
        # Byte 2: TPL[5:0] STL_high[1:0]
        # Byte 3: STL_low[7:0]
        byte0 = ((self.scid & 0x3F) << 2) | (start_addr_high & 0x03)
        byte1 = start_addr_low & 0xFF
        byte2 = ((self.tpl & 0x3F) << 2) | (stl_high & 0x03)
        byte3 = stl_low & 0xFF

        return struct.pack('<BBBB', byte0, byte1, byte2, byte3)

    @classmethod
    def unpack(cls, data: bytes) -> 'EtiSTC':
        """Unpack from 4 bytes."""
        byte0, byte1, byte2, byte3 = struct.unpack('<BBBB', data[:4])

        start_addr_high = byte0 & 0x03
        scid = (byte0 >> 2) & 0x3F
        start_addr_low = byte1
        stl_high = byte2 & 0x03
        tpl = (byte2 >> 2) & 0x3F
        stl_low = byte3

        start_address = (start_addr_high << 8) | start_addr_low
        stl = (stl_high << 8) | stl_low

        return cls(scid=scid, start_address=start_address, tpl=tpl, stl=stl)


@dataclass
class EtiEOH:
    """
    End of Header (4 bytes).

    Layout:
        MNSC: 16 bits - Multiplex Network Signalling Channel
        CRC:  16 bits - CRC of header
    """
    mnsc: int = 0
    crc: int = 0

    def pack(self) -> bytes:
        """Pack to 4 bytes (big-endian for CRC)."""
        return struct.pack('>HH', self.mnsc, self.crc)

    @classmethod
    def unpack(cls, data: bytes) -> 'EtiEOH':
        """Unpack from 4 bytes."""
        mnsc, crc = struct.unpack('>HH', data[:4])
        return cls(mnsc=mnsc, crc=crc)


@dataclass
class EtiEOF:
    """
    End of Frame (4 bytes).

    Layout:
        CRC: 16 bits - CRC of data
        RFU: 16 bits - Reserved for future use
    """
    crc: int = 0
    rfu: int = 0xFFFF

    def pack(self) -> bytes:
        """Pack to 4 bytes (big-endian)."""
        return struct.pack('>HH', self.crc, self.rfu)

    @classmethod
    def unpack(cls, data: bytes) -> 'EtiEOF':
        """Unpack from 4 bytes."""
        crc, rfu = struct.unpack('>HH', data[:4])
        return cls(crc=crc, rfu=rfu)


@dataclass
class EtiTIST:
    """
    Time Stamp (4 bytes).

    Layout:
        TIST: 32 bits - Timestamp in 1/16.384 MHz ticks
    """
    tist: int = 0

    def pack(self) -> bytes:
        """Pack to 4 bytes (little-endian)."""
        return struct.pack('<I', self.tist)

    @classmethod
    def unpack(cls, data: bytes) -> 'EtiTIST':
        """Unpack from 4 bytes."""
        tist = struct.unpack('<I', data[:4])[0]
        return cls(tist=tist)


@dataclass
class EtiMNSCTime0:
    """
    MNSC Time field 0 (2 bytes).

    Layout (16 bits):
        type:       4 bits - Type identifier (always 0)
        identifier: 4 bits - Sub-type identifier
        rfa:        8 bits - Reserved for future applications
    """
    type: int = 0
    identifier: int = 0
    rfa: int = 0

    def pack(self) -> bytes:
        """Pack to 2 bytes."""
        byte0 = ((self.identifier & 0x0F) << 4) | (self.type & 0x0F)
        byte1 = self.rfa & 0xFF
        return struct.pack('<BB', byte0, byte1)


@dataclass
class EtiMNSCTime1:
    """
    MNSC Time field 1 (2 bytes) - Minutes and Seconds in BCD.

    Layout (16 bits):
        second_unit:   4 bits - Seconds units digit
        second_tens:   3 bits - Seconds tens digit
        accuracy:      1 bit  - Time accuracy flag
        minute_unit:   4 bits - Minutes units digit
        minute_tens:   3 bits - Minutes tens digit
        sync_to_frame: 1 bit  - Sync to frame flag
    """
    second_unit: int = 0
    second_tens: int = 0
    accuracy: int = 0
    minute_unit: int = 0
    minute_tens: int = 0
    sync_to_frame: int = 0

    def set_from_time(self, dt: datetime) -> None:
        """Set from datetime object (BCD encoding)."""
        self.second_unit = dt.second % 10
        self.second_tens = dt.second // 10
        self.minute_unit = dt.minute % 10
        self.minute_tens = dt.minute // 10

    def pack(self) -> bytes:
        """Pack to 2 bytes."""
        byte0 = ((self.accuracy & 0x01) << 7) | ((self.second_tens & 0x07) << 4) | (self.second_unit & 0x0F)
        byte1 = ((self.sync_to_frame & 0x01) << 7) | ((self.minute_tens & 0x07) << 4) | (self.minute_unit & 0x0F)
        return struct.pack('<BB', byte0, byte1)


@dataclass
class EtiMNSCTime2:
    """
    MNSC Time field 2 (2 bytes) - Hours and Days in BCD.

    Layout (16 bits):
        hour_unit: 4 bits - Hours units digit
        hour_tens: 4 bits - Hours tens digit
        day_unit:  4 bits - Day units digit
        day_tens:  4 bits - Day tens digit
    """
    hour_unit: int = 0
    hour_tens: int = 0
    day_unit: int = 0
    day_tens: int = 0

    def set_from_time(self, dt: datetime) -> None:
        """Set from datetime object (BCD encoding)."""
        self.hour_unit = dt.hour % 10
        self.hour_tens = dt.hour // 10
        self.day_unit = dt.day % 10
        self.day_tens = dt.day // 10

    def pack(self) -> bytes:
        """Pack to 2 bytes."""
        byte0 = ((self.hour_tens & 0x0F) << 4) | (self.hour_unit & 0x0F)
        byte1 = ((self.day_tens & 0x0F) << 4) | (self.day_unit & 0x0F)
        return struct.pack('<BB', byte0, byte1)


@dataclass
class EtiMNSCTime3:
    """
    MNSC Time field 3 (2 bytes) - Month and Year in BCD.

    Layout (16 bits):
        month_unit: 4 bits - Month units digit
        month_tens: 4 bits - Month tens digit
        year_unit:  4 bits - Year units digit (year - 2000)
        year_tens:  4 bits - Year tens digit
    """
    month_unit: int = 0
    month_tens: int = 0
    year_unit: int = 0
    year_tens: int = 0

    def set_from_time(self, dt: datetime) -> None:
        """Set from datetime object (BCD encoding, year from 2000)."""
        self.month_unit = dt.month % 10
        self.month_tens = dt.month // 10
        year_since_2000 = dt.year - 2000
        self.year_unit = year_since_2000 % 10
        self.year_tens = year_since_2000 // 10

    def pack(self) -> bytes:
        """Pack to 2 bytes."""
        byte0 = ((self.month_tens & 0x0F) << 4) | (self.month_unit & 0x0F)
        byte1 = ((self.year_tens & 0x0F) << 4) | (self.year_unit & 0x0F)
        return struct.pack('<BB', byte0, byte1)


@dataclass
class EtiFrame:
    """
    Complete ETI frame.

    An ETI frame consists of:
        - SYNC header (4 bytes)
        - FC header (4 bytes)
        - STC headers (4 bytes each, one per subchannel)
        - EOH (4 bytes)
        - FIC data (optional, 96 bytes when present)
        - Subchannel data (variable length)
        - EOF (4 bytes)
        - TIST (4 bytes, optional)
    """
    sync: EtiSync
    fc: EtiFC
    stc_headers: List[EtiSTC]
    eoh: EtiEOH
    fic_data: bytes
    subchannel_data: bytes
    eof: EtiEOF
    tist: EtiTIST | None = None

    def pack(self) -> bytes:
        """Pack complete ETI frame to bytes."""
        data = bytearray()

        # SYNC
        data.extend(self.sync.pack())

        # FC
        data.extend(self.fc.pack())

        # STC headers
        for stc in self.stc_headers:
            data.extend(stc.pack())

        # EOH
        data.extend(self.eoh.pack())

        # FIC data (if FICF=1)
        if self.fc.ficf:
            data.extend(self.fic_data)

        # Subchannel data
        data.extend(self.subchannel_data)

        # EOF
        data.extend(self.eof.pack())

        # TIST (optional)
        if self.tist:
            data.extend(self.tist.pack())

        return bytes(data)

    @classmethod
    def create_empty(cls, mode: int = 1, with_tist: bool = False) -> 'EtiFrame':
        """
        Create an empty ETI frame with no subchannels.

        Args:
            mode: Transmission mode (1-4)
            with_tist: Include TIST field

        Returns:
            Empty EtiFrame
        """
        sync = EtiSync()
        fc = EtiFC(fct=0, nst=0, ficf=1, mid=mode, fp=0, fl=0)
        eoh = EtiEOH(mnsc=0, crc=0)
        fic_data = bytes(96)  # Empty FIC (96 bytes when FICF=1)
        eof = EtiEOF(crc=0, rfu=0xFFFF)
        tist = EtiTIST(tist=0) if with_tist else None

        return cls(
            sync=sync,
            fc=fc,
            stc_headers=[],
            eoh=eoh,
            fic_data=fic_data,
            subchannel_data=b'',
            eof=eof,
            tist=tist
        )
