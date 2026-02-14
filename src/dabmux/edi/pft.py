"""
PFT (Protection, Fragmentation and Transport) layer for EDI.

This module implements packet fragmentation and optional Reed-Solomon FEC
for reliable EDI transmission over lossy networks.
"""
import struct
import math
from dataclasses import dataclass
from typing import List, Optional
from dabmux.utils.crc import crc16
from dabmux.fec.reed_solomon import ReedSolomonEncoder

# PFT constants
PF_SYNC = b"PF"
PF_RS_K = 207  # RS data word length
PF_RS_N = 255  # RS codeword length (207 data + 48 parity)
PF_RS_P = 48   # RS parity bytes


@dataclass
class PFTConfig:
    """
    PFT configuration parameters.
    """
    fec: bool = False           # Enable Reed-Solomon FEC
    fec_m: int = 0              # Maximum number of recoverable fragments (0-5)
    max_fragment_size: int = 1400  # Maximum fragment payload size (bytes)
    addr: bool = False          # Include source/dest addresses
    source_addr: int = 0        # Source address (16-bit)
    dest_addr: int = 0          # Destination address (16-bit)


@dataclass
class PFFragment:
    """
    PF Fragment: A single PFT packet fragment.
    """
    pseq: int           # PFT sequence number (16-bit)
    findex: int         # Fragment index (24-bit)
    fcount: int         # Total fragment count (24-bit)
    fec: bool           # FEC enabled flag
    addr: bool          # Address present flag
    payload: bytes      # Fragment payload data
    source: int = 0     # Source address (optional)
    dest: int = 0       # Destination address (optional)
    rs_k: int = 0       # RS data length (optional, if fec=True)
    rs_z: int = 0       # RS zero padding (optional, if fec=True)

    def assemble(self) -> bytes:
        """
        Assemble PF fragment into bytes.

        Structure:
        - Psync: 2 bytes = "PF"
        - Pseq: 2 bytes (PFT sequence number)
        - Findex: 3 bytes (24-bit fragment index)
        - Fcount: 3 bytes (24-bit fragment count)
        - Plen: 2 bytes (bit 15: FEC, bit 14: ADDR, bits 13-0: payload length)
        - RSk: 1 byte (if FEC=1)
        - RSz: 1 byte (if FEC=1)
        - Source: 2 bytes (if ADDR=1)
        - Dest: 2 bytes (if ADDR=1)
        - CRC: 2 bytes
        - Payload: fragment data
        """
        packet = bytearray()

        # Psync (2 bytes)
        packet.extend(PF_SYNC)

        # Pseq (2 bytes)
        packet.extend(struct.pack('>H', self.pseq & 0xFFFF))

        # Findex (3 bytes, 24-bit)
        packet.extend(struct.pack('>I', self.findex & 0xFFFFFF)[1:])

        # Fcount (3 bytes, 24-bit)
        packet.extend(struct.pack('>I', self.fcount & 0xFFFFFF)[1:])

        # Plen (2 bytes)
        plen = len(self.payload) & 0x3FFF  # 14 bits for length
        if self.fec:
            plen |= 0x8000
        if self.addr:
            plen |= 0x4000
        packet.extend(struct.pack('>H', plen))

        # RSk and RSz (if FEC enabled)
        if self.fec:
            packet.append(self.rs_k & 0xFF)
            packet.append(self.rs_z & 0xFF)

        # Source and Dest (if ADDR enabled)
        if self.addr:
            packet.extend(struct.pack('>HH', self.source, self.dest))

        # Calculate CRC over header (before adding CRC field)
        crc_value = crc16(bytes(packet))
        packet.extend(struct.pack('>H', crc_value))

        # Payload
        packet.extend(self.payload)

        return bytes(packet)

    @classmethod
    def parse(cls, data: bytes) -> Optional['PFFragment']:
        """
        Parse PF fragment from bytes.

        Args:
            data: PF fragment bytes

        Returns:
            Parsed PFFragment or None if invalid
        """
        if len(data) < 14:  # Minimum header size
            return None

        # Check Psync
        if data[:2] != PF_SYNC:
            return None

        # Parse header
        pseq = struct.unpack('>H', data[2:4])[0]
        findex = struct.unpack('>I', b'\x00' + data[4:7])[0]
        fcount = struct.unpack('>I', b'\x00' + data[7:10])[0]
        plen = struct.unpack('>H', data[10:12])[0]

        # Extract flags and length
        fec = bool(plen & 0x8000)
        addr = bool(plen & 0x4000)
        payload_len = plen & 0x3FFF

        offset = 12

        # Parse RSk and RSz (if FEC)
        rs_k = 0
        rs_z = 0
        if fec:
            if len(data) < offset + 2:
                return None
            rs_k = data[offset]
            rs_z = data[offset + 1]
            offset += 2

        # Parse addresses (if ADDR)
        source = 0
        dest = 0
        if addr:
            if len(data) < offset + 4:
                return None
            source, dest = struct.unpack('>HH', data[offset:offset + 4])
            offset += 4

        # Parse CRC
        if len(data) < offset + 2:
            return None
        crc_received = struct.unpack('>H', data[offset:offset + 2])[0]
        offset += 2

        # Verify CRC over header
        crc_calculated = crc16(data[:offset - 2])
        if crc_calculated != crc_received:
            return None

        # Extract payload
        if len(data) < offset + payload_len:
            return None
        payload = data[offset:offset + payload_len]

        return cls(
            pseq=pseq,
            findex=findex,
            fcount=fcount,
            fec=fec,
            addr=addr,
            payload=payload,
            source=source,
            dest=dest,
            rs_k=rs_k,
            rs_z=rs_z
        )


class PFTFragmenter:
    """
    Fragments AF packets into PF fragments with optional FEC.
    """

    def __init__(self, config: PFTConfig) -> None:
        """
        Initialize PFT fragmenter.

        Args:
            config: PFT configuration
        """
        self.config = config
        self._pseq = 0  # PFT sequence counter

    def fragment(self, af_packet: bytes) -> List[PFFragment]:
        """
        Fragment an AF packet into PF fragments.

        Args:
            af_packet: AF packet bytes

        Returns:
            List of PF fragments
        """
        if self.config.fec:
            return self._fragment_with_fec(af_packet)
        else:
            return self._fragment_without_fec(af_packet)

    def _fragment_without_fec(self, af_packet: bytes) -> List[PFFragment]:
        """
        Fragment without FEC (simple sequential fragmentation).

        Args:
            af_packet: AF packet bytes

        Returns:
            List of PF fragments
        """
        fragments = []
        data_len = len(af_packet)
        max_payload = self.config.max_fragment_size

        # Calculate number of fragments needed
        num_fragments = math.ceil(data_len / max_payload)

        # Create fragments
        for i in range(num_fragments):
            start = i * max_payload
            end = min(start + max_payload, data_len)
            payload = af_packet[start:end]

            fragment = PFFragment(
                pseq=self._pseq,
                findex=i,
                fcount=num_fragments,
                fec=False,
                addr=self.config.addr,
                payload=payload,
                source=self.config.source_addr,
                dest=self.config.dest_addr
            )
            fragments.append(fragment)

        # Increment sequence
        self._pseq = (self._pseq + 1) & 0xFFFF

        return fragments

    def _fragment_with_fec(self, af_packet: bytes) -> List[PFFragment]:
        """
        Fragment with Reed-Solomon FEC.

        This applies RS encoding to chunks of the AF packet, then
        fragments the protected data with interleaving.

        Args:
            af_packet: AF packet bytes

        Returns:
            List of PF fragments
        """
        # Calculate chunk parameters
        k = PF_RS_K  # 207 bytes per chunk (data)
        m = self.config.fec_m  # Recoverable fragments

        # Calculate number of chunks needed
        chunk_count = math.ceil(len(af_packet) / k)

        # Calculate chunk length (may be less than k for last chunk)
        chunk_len = math.ceil(len(af_packet) / chunk_count)

        # Zero-pad to chunk boundary
        zero_pad = chunk_count * chunk_len - len(af_packet)
        padded_data = af_packet + (b'\x00' * zero_pad)

        # Apply RS encoding to each chunk
        rs_encoder = ReedSolomonEncoder(n=PF_RS_N, k=k)
        rs_block = bytearray()

        for i in range(chunk_count):
            chunk_start = i * chunk_len
            chunk_end = chunk_start + chunk_len
            chunk_data = padded_data[chunk_start:chunk_end]

            # Pad chunk to k bytes if needed
            if len(chunk_data) < k:
                chunk_data += b'\x00' * (k - len(chunk_data))

            # Encode chunk with RS
            encoded_chunk = rs_encoder.encode(chunk_data)
            rs_block.extend(encoded_chunk)

        # Calculate fragment size
        # Max fragment payload: s_max = (c * 48) / (m + 1)
        s_max = (chunk_count * PF_RS_P) // (m + 1) if m > 0 else self.config.max_fragment_size

        # Calculate number of fragments
        num_fragments = math.ceil(len(rs_block) / s_max)

        # Calculate actual fragment size
        fragment_size = math.ceil(len(rs_block) / num_fragments)

        # Create fragments with interleaving (column-major order)
        fragments = []
        for i in range(num_fragments):
            # Extract fragment data (interleaved)
            fragment_data = bytearray()
            for j in range(fragment_size):
                idx = j * num_fragments + i
                if idx < len(rs_block):
                    fragment_data.append(rs_block[idx])

            fragment = PFFragment(
                pseq=self._pseq,
                findex=i,
                fcount=num_fragments,
                fec=True,
                addr=self.config.addr,
                payload=bytes(fragment_data),
                source=self.config.source_addr,
                dest=self.config.dest_addr,
                rs_k=chunk_len,
                rs_z=zero_pad
            )
            fragments.append(fragment)

        # Increment sequence
        self._pseq = (self._pseq + 1) & 0xFFFF

        return fragments

    def reset_counter(self) -> None:
        """Reset PFT sequence counter (for testing)."""
        self._pseq = 0
