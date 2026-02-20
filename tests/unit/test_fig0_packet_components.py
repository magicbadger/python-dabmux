"""
Tests for FIG 0/3: Service Component in Packet Mode.

Per ETSI EN 300 401 Section 8.1.4.
"""
import pytest
from dabmux.fig.fig0 import FIG0_3
from dabmux.fig.base import FIGRate, FIGPriority
from dabmux.core.mux_elements import (
    DabEnsemble,
    DabService,
    DabComponent,
    DabPacketComponent,
    DabSubchannel,
    DabLabel,
    DabProtection,
    SubchannelType,
    ProtectionForm,
    DabProtectionEEP,
    EEPProfile,
    UserApplication,
)


def create_test_ensemble() -> DabEnsemble:
    """Create a test ensemble."""
    ensemble = DabEnsemble(
        id=0xCE15,
        label=DabLabel(text="Test Ensemble"),
        ecc=0xE1,
    )
    return ensemble


def create_packet_subchannel(subchan_id: int) -> DabSubchannel:
    """Create a packet mode subchannel."""
    protection = DabProtection(
        form=ProtectionForm.EEP,
        level=2,  # EEP 3-A
        eep=DabProtectionEEP(profile=EEPProfile.EEP_A)
    )
    return DabSubchannel(
        uid=f'packet_{subchan_id}',
        id=subchan_id,
        type=SubchannelType.Packet,
        start_address=0,
        bitrate=64,
        protection=protection,
        input_uri='file://test.bin',
        fec_scheme=1
    )


def create_programme_service(service_id: int) -> DabService:
    """Create a programme service (16-bit SId)."""
    return DabService(
        uid=f'service_{service_id}',
        id=service_id,
        label=DabLabel(text=f'Service {service_id}')
    )


def create_data_service(service_id: int) -> DabService:
    """Create a data service (32-bit SId)."""
    return DabService(
        uid=f'data_service_{service_id}',
        id=service_id,
        label=DabLabel(text=f'Data Service {service_id:08X}')
    )


def create_packet_component(service_id: int, subchan_id: int, packet_addr: int = 0, dscty: int = 60) -> DabComponent:
    """Create a packet mode component."""
    return DabComponent(
        uid=f'component_{service_id}_{subchan_id}',
        service_id=service_id,
        subchannel_id=subchan_id,
        is_packet_mode=True,
        packet=DabPacketComponent(
            id=0,
            address=packet_addr,
            datagroup=True,
            dscty=dscty,
            ca_org=0
        )
    )


class TestFIG0_3:
    """Tests for FIG 0/3: Service Component in Packet Mode."""

    def test_header_encoding(self) -> None:
        """Test FIG 0/3 header encoding."""
        ensemble = create_test_ensemble()
        ensemble.services.append(create_programme_service(0x5001))
        ensemble.subchannels.append(create_packet_subchannel(0))
        ensemble.components.append(create_packet_component(0x5001, 0))

        fig = FIG0_3(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        assert status.num_bytes_written == 8  # 2 header + 3 service + 3 component
        assert status.complete_fig_transmitted is True

        # Check header
        # Byte 0: Type (3 bits) = 0, Length (5 bits) = 7 (1 header + 3 service + 3 component)
        assert buf[0] == 0x07

        # Byte 1: CN=0, OE=0, PD=0 (programme), Extension=3
        assert buf[1] == 0x03

    def test_single_packet_component(self) -> None:
        """Test encoding single packet component."""
        ensemble = create_test_ensemble()
        ensemble.services.append(create_programme_service(0x5001))
        ensemble.subchannels.append(create_packet_subchannel(5))
        ensemble.components.append(create_packet_component(0x5001, 5, packet_addr=123, dscty=60))

        fig = FIG0_3(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        assert status.num_bytes_written == 8
        assert status.complete_fig_transmitted is True

        # Service header (programme): 3 bytes
        assert buf[2:4] == bytes([0x50, 0x01])  # SId = 0x5001
        assert buf[4] == 0x01  # Local=0, CAId=0, NbComponents=1

        # Component data: 3 bytes
        # Byte 0: TMid (2) | DSCTy (6)
        # TMid=01 (packet), DSCTy=60 → (1 << 6) | 60 = 0x7C
        assert buf[5] == 0x7C

        # Byte 1: SubChId (6) | Packet Address High (2)
        # SubChId=5, Addr=123 → (5 << 2) | (123 >> 8) = 0x14
        assert buf[6] == 0x14

        # Byte 2: Packet Address Low (8)
        # Addr low = 123 & 0xFF = 0x7B
        assert buf[7] == 0x7B

    def test_multiple_packet_components(self) -> None:
        """Test encoding multiple packet components per service."""
        ensemble = create_test_ensemble()
        ensemble.services.append(create_programme_service(0x5001))
        ensemble.subchannels.append(create_packet_subchannel(0))
        ensemble.components.append(create_packet_component(0x5001, 0, packet_addr=0, dscty=60))
        ensemble.components.append(create_packet_component(0x5001, 0, packet_addr=1, dscty=24))

        fig = FIG0_3(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        assert status.num_bytes_written == 11  # 2 header + 3 service + 3 + 3 components
        assert buf[4] == 0x02  # NbComponents=2

        # First component (addr=0, dscty=60)
        assert buf[5] == 0x7C  # TMid=01, DSCTy=60
        assert buf[6] == 0x00  # SubChId=0, Addr high=0
        assert buf[7] == 0x00  # Addr low=0

        # Second component (addr=1, dscty=24)
        assert buf[8] == 0x58  # TMid=01, DSCTy=24
        assert buf[9] == 0x00  # SubChId=0, Addr high=0
        assert buf[10] == 0x01  # Addr low=1

    def test_tmid_encoding(self) -> None:
        """Test that TMid is correctly set to 01 (packet mode)."""
        ensemble = create_test_ensemble()
        ensemble.services.append(create_programme_service(0x5001))
        ensemble.subchannels.append(create_packet_subchannel(0))
        ensemble.components.append(create_packet_component(0x5001, 0, dscty=60))

        fig = FIG0_3(ensemble)
        buf = bytearray(32)
        fig.fill(buf, 32)

        # Component byte 0: TMid (bits 7-6) should be 01
        tmid = (buf[5] >> 6) & 0x03
        assert tmid == 1  # Packet mode

    def test_dscty_encoding(self) -> None:
        """Test different DSCTy values."""
        ensemble = create_test_ensemble()
        ensemble.services.append(create_programme_service(0x5001))
        ensemble.subchannels.append(create_packet_subchannel(0))
        ensemble.components.append(create_packet_component(0x5001, 0, dscty=5))   # Journaline
        ensemble.components.append(create_packet_component(0x5001, 0, dscty=24))  # EPG
        ensemble.components.append(create_packet_component(0x5001, 0, dscty=60))  # MOT

        fig = FIG0_3(ensemble)
        buf = bytearray(32)
        fig.fill(buf, 32)

        # DSCTy values (bits 5-0 of component byte 0)
        assert (buf[5] & 0x3F) == 5   # Journaline
        assert (buf[8] & 0x3F) == 24  # EPG
        assert (buf[11] & 0x3F) == 60  # MOT

    def test_packet_address_encoding(self) -> None:
        """Test packet address encoding (10 bits, 0-1023)."""
        ensemble = create_test_ensemble()
        ensemble.services.append(create_programme_service(0x5001))
        ensemble.subchannels.append(create_packet_subchannel(0))
        ensemble.components.append(create_packet_component(0x5001, 0, packet_addr=0))      # Min
        ensemble.components.append(create_packet_component(0x5001, 0, packet_addr=512))    # Mid
        ensemble.components.append(create_packet_component(0x5001, 0, packet_addr=1023))   # Max

        fig = FIG0_3(ensemble)
        buf = bytearray(32)
        fig.fill(buf, 32)

        # Address 0: high=0, low=0
        assert buf[6] == 0x00
        assert buf[7] == 0x00

        # Address 512 (0x200): high=2, low=0
        assert buf[9] == 0x02  # SubChId=0 (bits 7-2) | High=2 (bits 1-0)
        assert buf[10] == 0x00

        # Address 1023 (0x3FF): high=3, low=255
        assert buf[12] == 0x03  # SubChId=0 | High=3
        assert buf[13] == 0xFF

    def test_subchannel_id_encoding(self) -> None:
        """Test subchannel ID encoding (6 bits)."""
        ensemble = create_test_ensemble()
        ensemble.services.append(create_programme_service(0x5001))
        ensemble.subchannels.append(create_packet_subchannel(0))
        ensemble.subchannels.append(create_packet_subchannel(31))
        ensemble.subchannels.append(create_packet_subchannel(63))
        ensemble.components.append(create_packet_component(0x5001, 0, packet_addr=0))
        ensemble.components.append(create_packet_component(0x5001, 31, packet_addr=0))
        ensemble.components.append(create_packet_component(0x5001, 63, packet_addr=0))

        fig = FIG0_3(ensemble)
        buf = bytearray(32)
        fig.fill(buf, 32)

        # SubChId encoding (bits 7-2 of component byte 1)
        assert (buf[6] >> 2) == 0   # SubChId=0
        assert (buf[9] >> 2) == 31  # SubChId=31
        assert (buf[12] >> 2) == 63  # SubChId=63

    def test_programme_service_header(self) -> None:
        """Test programme service header (16-bit SId, 3 bytes)."""
        ensemble = create_test_ensemble()
        ensemble.services.append(create_programme_service(0xABCD))
        ensemble.subchannels.append(create_packet_subchannel(0))
        ensemble.components.append(create_packet_component(0xABCD, 0))

        fig = FIG0_3(ensemble)
        buf = bytearray(32)
        fig.fill(buf, 32)

        # Service header: 3 bytes
        assert buf[2:4] == bytes([0xAB, 0xCD])  # 16-bit SId
        assert buf[4] == 0x01  # NbComponents=1

    def test_data_service_header(self) -> None:
        """Test data service header (32-bit SId, 5 bytes)."""
        ensemble = create_test_ensemble()
        ensemble.services.append(create_data_service(0xD0001234))
        ensemble.subchannels.append(create_packet_subchannel(0))
        ensemble.components.append(create_packet_component(0xD0001234, 0))

        fig = FIG0_3(ensemble)

        # First call automatically switches to data services (no programme services exist)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        assert status.num_bytes_written == 10  # 2 header + 5 service + 3 component
        assert status.complete_fig_transmitted is True

        # Check header PD flag (should be 1 for data services)
        assert (buf[1] >> 5) & 0x01 == 1

        # Service header: 5 bytes
        assert buf[2:6] == bytes([0xD0, 0x00, 0x12, 0x34])  # 32-bit SId
        assert buf[6] == 0x01  # NbComponents=1

    def test_no_packet_components(self) -> None:
        """Test behavior when no packet components exist."""
        ensemble = create_test_ensemble()
        ensemble.services.append(create_programme_service(0x5001))

        fig = FIG0_3(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        assert status.num_bytes_written == 0
        assert status.complete_fig_transmitted is True

    def test_mixed_stream_packet_components(self) -> None:
        """Test that only packet mode components are included."""
        ensemble = create_test_ensemble()
        ensemble.services.append(create_programme_service(0x5001))
        ensemble.subchannels.append(create_packet_subchannel(0))

        # Add stream mode component (should be ignored)
        stream_comp = DabComponent(
            uid='stream',
            service_id=0x5001,
            subchannel_id=0,
            is_packet_mode=False
        )
        ensemble.components.append(stream_comp)

        # Add packet mode component (should be included)
        ensemble.components.append(create_packet_component(0x5001, 0))

        fig = FIG0_3(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Should only include packet component
        assert status.num_bytes_written == 8
        assert buf[4] == 0x01  # Only 1 component

    def test_programme_data_alternation(self) -> None:
        """Test alternation between programme and data services."""
        ensemble = create_test_ensemble()
        ensemble.services.append(create_programme_service(0x5001))
        ensemble.services.append(create_data_service(0xD0000001))
        ensemble.subchannels.append(create_packet_subchannel(0))
        ensemble.components.append(create_packet_component(0x5001, 0))
        ensemble.components.append(create_packet_component(0xD0000001, 0))

        fig = FIG0_3(ensemble)

        # First call: programme services (PD=0)
        buf1 = bytearray(32)
        status1 = fig.fill(buf1, 32)
        assert status1.complete_fig_transmitted is False
        assert (buf1[1] >> 5) & 0x01 == 0  # PD=0

        # Second call: data services (PD=1)
        buf2 = bytearray(32)
        status2 = fig.fill(buf2, 32)
        assert status2.complete_fig_transmitted is True
        assert (buf2[1] >> 5) & 0x01 == 1  # PD=1

    def test_iterative_transmission(self) -> None:
        """Test iterative transmission across multiple services."""
        ensemble = create_test_ensemble()

        # Add 3 programme services with packet components
        for i in range(3):
            sid = 0x5000 + i
            ensemble.services.append(create_programme_service(sid))
            ensemble.subchannels.append(create_packet_subchannel(i))
            ensemble.components.append(create_packet_component(sid, i))

        fig = FIG0_3(ensemble)

        # First call with limited space (header + 1 service + component)
        buf1 = bytearray(32)
        status1 = fig.fill(buf1, 8)  # Only space for 1 service

        assert status1.num_bytes_written == 8
        assert status1.complete_fig_transmitted is False

        # Second call should continue
        buf2 = bytearray(32)
        status2 = fig.fill(buf2, 8)

        assert status2.num_bytes_written == 8
        assert status2.complete_fig_transmitted is False

        # Third call should complete
        buf3 = bytearray(32)
        status3 = fig.fill(buf3, 32)

        assert status3.num_bytes_written == 8
        assert status3.complete_fig_transmitted is True

    def test_insufficient_space(self) -> None:
        """Test behavior with insufficient buffer space."""
        ensemble = create_test_ensemble()
        ensemble.services.append(create_programme_service(0x5001))
        ensemble.subchannels.append(create_packet_subchannel(0))
        ensemble.components.append(create_packet_component(0x5001, 0))

        fig = FIG0_3(ensemble)

        # Not enough space for even the header
        buf = bytearray(32)
        status = fig.fill(buf, 1)

        assert status.num_bytes_written == 0
        assert status.complete_fig_transmitted is False

    def test_repetition_rate(self) -> None:
        """Test that FIG 0/3 has correct repetition rate."""
        ensemble = create_test_ensemble()
        fig = FIG0_3(ensemble)

        assert fig.repetition_rate() == FIGRate.B  # Once per second

    def test_priority(self) -> None:
        """Test that FIG 0/3 has correct priority."""
        ensemble = create_test_ensemble()
        fig = FIG0_3(ensemble)

        assert fig.priority() == FIGPriority.HIGH

    def test_fig_type_extension(self) -> None:
        """Test FIG type and extension values."""
        ensemble = create_test_ensemble()
        fig = FIG0_3(ensemble)

        assert fig.fig_type() == 0
        assert fig.fig_extension() == 3

    def test_component_size_difference(self) -> None:
        """Test that packet components are 3 bytes (vs 2 bytes for stream mode)."""
        ensemble = create_test_ensemble()
        ensemble.services.append(create_programme_service(0x5001))
        ensemble.subchannels.append(create_packet_subchannel(0))
        ensemble.components.append(create_packet_component(0x5001, 0))

        fig = FIG0_3(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Total: 2 (header) + 3 (service header) + 3 (component) = 8 bytes
        assert status.num_bytes_written == 8
