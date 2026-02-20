#!/usr/bin/env python3
"""
EDI Test Generator

Generates synthetic EDI packets for testing receivers/modulators.
Useful for validation and stress testing.

Usage:
    # Generate and send to UDP
    python edi_generator.py --udp 192.168.1.100:12000 --count 100

    # Generate with PFT
    python edi_generator.py --udp 239.1.2.3:12000 --pft --fec 3

    # Generate to file
    python edi_generator.py --file test.edi --count 1000

    # Continuous generation
    python edi_generator.py --udp 127.0.0.1:12000 --continuous

    # Custom ensemble ID
    python edi_generator.py --udp 127.0.0.1:12000 --ensemble-id 0xABCD
"""
import argparse
import socket
import struct
import sys
import time
from pathlib import Path


class EDIGenerator:
    """Generate synthetic EDI packets."""

    def __init__(self, ensemble_id=0xCE15, enable_pft=False, fec_depth=0):
        self.ensemble_id = ensemble_id
        self.enable_pft = enable_pft
        self.fec_depth = fec_depth
        self.seq_number = 0
        self.frame_count = 0

    def create_ptr_tag(self) -> bytes:
        """Create *ptr TAG (protocol type)."""
        name = b"*ptr"
        value = b"DETI"  # DAB ETI protocol
        length_bits = len(value) * 8

        return name + struct.pack('>I', length_bits) + value

    def create_tist_tag(self) -> bytes:
        """Create tist TAG (timestamp)."""
        name = b"tist"

        # Current time since EDI epoch (2000-01-01)
        import time as time_module
        EDI_EPOCH_UNIX = 946684800
        current_time = time_module.time()
        edi_seconds = int(current_time - EDI_EPOCH_UNIX)
        subsec = current_time - int(current_time)
        ticks = int(subsec * 16384) & 0xFFFFFF

        # Pack as 56-bit value (7 bytes)
        timestamp = (edi_seconds << 24) | ticks
        value = struct.pack('>Q', timestamp)[1:]  # Take last 7 bytes

        length_bits = len(value) * 8

        return name + struct.pack('>I', length_bits) + value

    def create_deti_tag(self) -> bytes:
        """Create deti TAG (DAB ETI data)."""
        name = b"deti"

        # Minimal DETI structure
        dlfc = self.frame_count & 0xFFFFFF  # 24-bit frame count
        stat = 0xFF  # No error
        mid = 1  # Mode I
        fp = 0  # No frame phase

        # Build DETI value
        value = bytearray()
        value.extend(struct.pack('>I', dlfc)[1:])  # 24-bit DLFC
        value.append(stat)
        value.append((mid << 6) | fp)

        # Add dummy ETI data (simplified)
        # In reality, this would contain actual ETI frame data
        eti_dummy = bytes(100)  # Placeholder
        value.extend(eti_dummy)

        length_bits = len(value) * 8

        return name + struct.pack('>I', length_bits) + bytes(value)

    def create_af_packet(self) -> bytes:
        """Create AF (Assembly Format) packet."""
        # Build TAG packet
        tag_packet = bytearray()
        tag_packet.extend(self.create_ptr_tag())
        tag_packet.extend(self.create_tist_tag())
        tag_packet.extend(self.create_deti_tag())

        # Pad to 8-byte boundary
        while len(tag_packet) % 8 != 0:
            tag_packet.append(0)

        # Build AF packet
        af_packet = bytearray()

        # SYNC (2 bytes): "AF"
        af_packet.extend(b'AF')

        # LEN (4 bytes): payload length in bits
        length_bits = len(tag_packet) * 8
        af_packet.extend(struct.pack('>I', length_bits))

        # SEQ (2 bytes): sequence number
        af_packet.extend(struct.pack('>H', self.seq_number))

        # Payload
        af_packet.extend(tag_packet)

        # CRC (2 bytes): simplified CRC
        crc = self._calculate_crc16(bytes(af_packet))
        af_packet.extend(struct.pack('>H', crc))

        self.seq_number = (self.seq_number + 1) % 65536
        self.frame_count += 1

        return bytes(af_packet)

    def create_pft_packets(self, af_packet: bytes) -> list:
        """Fragment AF packet into PFT packets."""
        fragment_size = 1400  # Standard MTU-based size

        # Split into fragments
        fragments = []
        offset = 0
        while offset < len(af_packet):
            fragment = af_packet[offset:offset + fragment_size]
            fragments.append(fragment)
            offset += fragment_size

        # Create PFT packets
        pft_packets = []
        for i, fragment in enumerate(fragments):
            pft_packet = self._create_pft_packet(fragment, i, len(fragments))
            pft_packets.append(pft_packet)

        # Add FEC parity packets if enabled
        if self.fec_depth > 0:
            # Simplified: just add dummy parity packets
            for i in range(self.fec_depth):
                parity_data = bytes(fragment_size)  # Dummy parity
                pft_packet = self._create_pft_packet(parity_data, len(fragments) + i, len(fragments) + self.fec_depth)
                pft_packets.append(pft_packet)

        return pft_packets

    def _create_pft_packet(self, fragment: bytes, index: int, total: int) -> bytes:
        """Create single PFT packet."""
        pft = bytearray()

        # SYNC (2 bytes): "PF"
        pft.extend(b'PF')

        # PSEQ (2 bytes): PFT sequence number
        pft.extend(struct.pack('>H', self.seq_number))

        # FINDEX (3 bytes): fragment index
        pft.extend(struct.pack('>I', index)[1:])

        # FCOUNT (1 byte): total fragments
        pft.append(total & 0xFF)

        # FEC params (1 byte)
        fec_byte = 0
        if self.fec_depth > 0:
            fec_byte = 0x80 | (self.fec_depth & 0x1F)
        pft.append(fec_byte)

        # ADDR (2 bytes): destination address
        pft.extend(struct.pack('>H', 0))

        # Payload
        pft.extend(fragment)

        return bytes(pft)

    def _calculate_crc16(self, data: bytes) -> int:
        """Simple CRC-16 calculation."""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
                crc &= 0xFFFF
        return crc

    def generate_packet(self) -> bytes:
        """Generate one EDI packet (or packet set)."""
        af_packet = self.create_af_packet()

        if self.enable_pft:
            # Return first PFT packet (simplified)
            pft_packets = self.create_pft_packets(af_packet)
            return pft_packets[0] if pft_packets else af_packet
        else:
            return af_packet


def main():
    parser = argparse.ArgumentParser(
        description='EDI Test Generator',
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    output_group = parser.add_mutually_exclusive_group(required=True)
    output_group.add_argument('--udp', metavar='HOST:PORT',
                             help='Send to UDP destination')
    output_group.add_argument('--file', metavar='PATH',
                             help='Write to file')

    parser.add_argument('-n', '--count', type=int, default=100,
                       help='Number of packets to generate (default: 100)')
    parser.add_argument('--continuous', action='store_true',
                       help='Generate continuously until interrupted')
    parser.add_argument('--ensemble-id', type=lambda x: int(x, 0), default=0xCE15,
                       help='Ensemble ID in hex (default: 0xCE15)')
    parser.add_argument('--pft', action='store_true',
                       help='Enable PFT fragmentation')
    parser.add_argument('--fec', type=int, default=0, metavar='DEPTH',
                       help='FEC depth for PFT (0-7, default: 0)')
    parser.add_argument('--rate', type=int, default=10, metavar='FPS',
                       help='Frames per second (default: 10)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Verbose output')

    args = parser.parse_args()

    # Validate
    if args.fec < 0 or args.fec > 7:
        print("Error: FEC depth must be 0-7")
        return 1

    if args.fec > 0 and not args.pft:
        print("Error: --fec requires --pft")
        return 1

    # Create generator
    generator = EDIGenerator(
        ensemble_id=args.ensemble_id,
        enable_pft=args.pft,
        fec_depth=args.fec
    )

    # Setup output
    sock = None
    output_file = None

    if args.udp:
        if ':' not in args.udp:
            print("Error: UDP format must be HOST:PORT")
            return 1

        host, port_str = args.udp.rsplit(':', 1)
        port = int(port_str)

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print(f"Sending EDI packets to {host}:{port}")

    elif args.file:
        output_file = open(args.file, 'wb')
        print(f"Writing EDI packets to {args.file}")

    # Generate packets
    count = args.count if not args.continuous else 0
    packets_sent = 0
    frame_delay = 1.0 / args.rate if args.rate > 0 else 0.1

    try:
        while args.continuous or packets_sent < count:
            packet = generator.generate_packet()

            if sock:
                sock.sendto(packet, (host, port))
            elif output_file:
                output_file.write(packet)

            packets_sent += 1

            if args.verbose:
                print(f"Sent packet #{packets_sent}, size: {len(packet)} bytes")

            time.sleep(frame_delay)

    except KeyboardInterrupt:
        print("\nStopped by user")

    finally:
        if sock:
            sock.close()
        if output_file:
            output_file.close()

    print(f"\nGenerated {packets_sent} packets")

    return 0


if __name__ == '__main__':
    sys.exit(main())
