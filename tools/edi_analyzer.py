#!/usr/bin/env python3
"""
EDI Packet Analyzer

Analyzes EDI packets from UDP or file, displaying TAG structure and contents.
Useful for debugging and validation of EDI streams.

Usage:
    # Analyze UDP stream
    python edi_analyzer.py --udp 127.0.0.1:12000

    # Analyze from file
    python edi_analyzer.py --file captured.edi

    # Verbose mode with full TAG dumps
    python edi_analyzer.py --udp 127.0.0.1:12000 --verbose

    # Save analysis to file
    python edi_analyzer.py --udp 127.0.0.1:12000 --output report.txt
"""
import argparse
import socket
import struct
import sys
from datetime import datetime
from pathlib import Path


class AFPacketParser:
    """Parse AF (Assembly Format) packets."""

    @staticmethod
    def parse(data: bytes) -> dict:
        """
        Parse AF packet.

        Returns:
            Dictionary with packet info or None if invalid
        """
        if len(data) < 10:
            return None

        # Check sync
        sync = struct.unpack('>H', data[0:2])[0]
        if sync != 0x4146:  # "AF"
            return None

        # Parse header
        length = struct.unpack('>I', data[2:6])[0]
        seq = struct.unpack('>H', data[6:8])[0]

        # Extract payload
        payload = data[8:-2] if len(data) > 10 else b""
        crc = struct.unpack('>H', data[-2:])[0] if len(data) >= 10 else 0

        return {
            'type': 'AF',
            'sync': sync,
            'length': length,
            'seq': seq,
            'payload': payload,
            'crc': crc,
            'total_size': len(data)
        }


class PFTPacketParser:
    """Parse PFT (Protection, Fragmentation and Transport) packets."""

    @staticmethod
    def parse(data: bytes) -> dict:
        """Parse PFT packet."""
        if len(data) < 14:
            return None

        # Check sync
        sync = struct.unpack('>H', data[0:2])[0]
        if sync != 0x5046:  # "PF"
            return None

        # Parse PFT header
        pseq = struct.unpack('>H', data[2:4])[0]
        findex = struct.unpack('>I', data[4:8])[0] & 0xFFFFFF
        fcount = data[7]
        fec_params = data[8]
        addr = struct.unpack('>H', data[9:11])[0]

        has_fec = (fec_params & 0x80) != 0
        fec_m = fec_params & 0x1F if has_fec else 0

        return {
            'type': 'PFT',
            'sync': sync,
            'pseq': pseq,
            'findex': findex,
            'fcount': fcount,
            'has_fec': has_fec,
            'fec_m': fec_m,
            'addr': addr,
            'total_size': len(data)
        }


class TAGParser:
    """Parse EDI TAG items."""

    @staticmethod
    def parse_tags(data: bytes) -> list:
        """Parse all TAG items from data."""
        tags = []
        offset = 0

        while offset + 8 <= len(data):
            # Parse TAG header
            name = data[offset:offset+4]
            length_bits = struct.unpack('>I', data[offset+4:offset+8])[0]
            length_bytes = (length_bits + 7) // 8

            if offset + 8 + length_bytes > len(data):
                break

            value = data[offset+8:offset+8+length_bytes]

            tags.append({
                'name': name.decode('ascii', errors='replace'),
                'length_bits': length_bits,
                'length_bytes': length_bytes,
                'value': value
            })

            offset += 8 + length_bytes

        return tags

    @staticmethod
    def decode_tag(tag: dict) -> str:
        """Decode TAG content for display."""
        name = tag['name']
        value = tag['value']

        if name == '*ptr':
            # Protocol type
            protocol = value.decode('ascii', errors='replace')
            return f"Protocol: {protocol}"

        elif name == 'tist':
            # Timestamp
            if len(value) >= 7:
                timestamp_int = struct.unpack('>Q', b'\x00' + value)[0]
                seconds = (timestamp_int >> 24) & 0xFFFFFFFF
                ticks = timestamp_int & 0xFFFFFF
                subsec = ticks / 16384.0
                return f"Time: {seconds}s + {subsec:.6f}s ({ticks} ticks)"

        elif name == 'deti':
            # DAB ETI data
            if len(value) >= 4:
                dlfc = struct.unpack('>I', value[0:4])[0] & 0xFFFFFF
                return f"Frame count: {dlfc}"

        elif name.startswith('est'):
            # Stream characteristics
            return f"Stream data ({len(value)} bytes)"

        # Default: show hex
        return f"Data: {value[:16].hex()}{'...' if len(value) > 16 else ''}"


class EDIAnalyzer:
    """Main EDI analyzer."""

    def __init__(self, verbose=False, output_file=None):
        self.verbose = verbose
        self.output_file = output_file
        self.stats = {
            'af_packets': 0,
            'pft_packets': 0,
            'tags_seen': set(),
            'total_bytes': 0,
            'errors': 0
        }

    def log(self, message):
        """Log message to console and optionally file."""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        full_msg = f"[{timestamp}] {message}"
        print(full_msg)

        if self.output_file:
            with open(self.output_file, 'a') as f:
                f.write(full_msg + '\n')

    def analyze_packet(self, data: bytes):
        """Analyze a single packet."""
        self.stats['total_bytes'] += len(data)

        # Try AF packet
        af_info = AFPacketParser.parse(data)
        if af_info:
            self.stats['af_packets'] += 1
            self.log(f"\n=== AF Packet #{self.stats['af_packets']} ===")
            self.log(f"  Sequence: {af_info['seq']}")
            self.log(f"  Length: {af_info['length']} bits ({af_info['total_size']} bytes)")
            self.log(f"  CRC: 0x{af_info['crc']:04X}")

            # Parse TAGs
            tags = TAGParser.parse_tags(af_info['payload'])
            self.log(f"  TAGs: {len(tags)}")

            for tag in tags:
                self.stats['tags_seen'].add(tag['name'])
                decoded = TAGParser.decode_tag(tag)
                self.log(f"    - {tag['name']}: {decoded}")

                if self.verbose:
                    self.log(f"      Raw: {tag['value'][:32].hex()}{'...' if len(tag['value']) > 32 else ''}")

            return

        # Try PFT packet
        pft_info = PFTPacketParser.parse(data)
        if pft_info:
            self.stats['pft_packets'] += 1
            self.log(f"\n=== PFT Packet #{self.stats['pft_packets']} ===")
            self.log(f"  Sequence: {pft_info['pseq']}")
            self.log(f"  Fragment: {pft_info['findex']+1}/{pft_info['fcount']}")
            self.log(f"  FEC: {'Yes' if pft_info['has_fec'] else 'No'}")
            if pft_info['has_fec']:
                self.log(f"  FEC M: {pft_info['fec_m']}")
            self.log(f"  Size: {pft_info['total_size']} bytes")
            return

        # Unknown packet
        self.stats['errors'] += 1
        self.log(f"\n=== Unknown Packet ===")
        self.log(f"  Size: {len(data)} bytes")
        self.log(f"  Header: {data[:16].hex() if len(data) >= 16 else data.hex()}")

    def print_statistics(self):
        """Print analysis statistics."""
        self.log("\n" + "="*60)
        self.log("STATISTICS")
        self.log("="*60)
        self.log(f"AF Packets: {self.stats['af_packets']}")
        self.log(f"PFT Packets: {self.stats['pft_packets']}")
        self.log(f"Unknown/Errors: {self.stats['errors']}")
        self.log(f"Total Bytes: {self.stats['total_bytes']:,}")
        self.log(f"TAGs Seen: {', '.join(sorted(self.stats['tags_seen']))}")

    def analyze_udp(self, host: str, port: int, count: int = 0):
        """Analyze EDI packets from UDP."""
        self.log(f"Listening on UDP {host}:{port}")
        self.log(f"Press Ctrl+C to stop\n")

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))

        # Join multicast if needed
        if host.startswith("239."):
            import struct
            mreq = struct.pack("4sl", socket.inet_aton(host), socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        packets_received = 0

        try:
            while count == 0 or packets_received < count:
                data, addr = sock.recvfrom(65536)
                packets_received += 1
                self.analyze_packet(data)
        except KeyboardInterrupt:
            self.log("\n\nStopped by user")
        finally:
            sock.close()
            self.print_statistics()

    def analyze_file(self, filepath: Path):
        """Analyze EDI packets from file."""
        self.log(f"Analyzing file: {filepath}\n")

        if not filepath.exists():
            self.log(f"Error: File not found: {filepath}")
            return

        with open(filepath, 'rb') as f:
            data = f.read()

        # Try to parse as continuous stream
        offset = 0
        packet_count = 0

        while offset < len(data):
            # Look for AF or PF sync
            remaining = data[offset:]

            # Try AF
            if remaining.startswith(b'AF'):
                # Find packet length
                if len(remaining) >= 6:
                    length = struct.unpack('>I', remaining[2:6])[0]
                    packet_size = 10 + ((length + 7) // 8)

                    if offset + packet_size <= len(data):
                        packet_count += 1
                        self.analyze_packet(remaining[:packet_size])
                        offset += packet_size
                        continue

            # Try PF
            if remaining.startswith(b'PF'):
                # PFT packets are variable length, estimate
                packet_size = min(1500, len(remaining))
                packet_count += 1
                self.analyze_packet(remaining[:packet_size])
                offset += packet_size
                continue

            # Skip byte
            offset += 1

        self.log(f"\nProcessed {packet_count} packets")
        self.print_statistics()


def main():
    parser = argparse.ArgumentParser(
        description='EDI Packet Analyzer',
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument('--udp', metavar='HOST:PORT',
                             help='Analyze UDP stream (e.g., 127.0.0.1:12000)')
    source_group.add_argument('--file', metavar='PATH',
                             help='Analyze EDI file')

    parser.add_argument('-n', '--count', type=int, default=0,
                       help='Number of packets to capture (0=unlimited)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Verbose output (show raw TAG data)')
    parser.add_argument('-o', '--output', metavar='FILE',
                       help='Save analysis to file')

    args = parser.parse_args()

    analyzer = EDIAnalyzer(verbose=args.verbose, output_file=args.output)

    if args.udp:
        if ':' not in args.udp:
            print("Error: UDP format must be HOST:PORT")
            return 1

        host, port_str = args.udp.rsplit(':', 1)
        port = int(port_str)

        analyzer.analyze_udp(host, port, count=args.count)

    elif args.file:
        filepath = Path(args.file)
        analyzer.analyze_file(filepath)

    return 0


if __name__ == '__main__':
    sys.exit(main())
