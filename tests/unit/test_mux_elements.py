"""
Unit tests for MuxElements (ensemble configuration).

These tests verify the ensemble configuration structures work correctly.
"""
import pytest
from dabmux.core.mux_elements import (
    DabLabel, DabProtection, DabProtectionUEP, DabProtectionEEP,
    DabSubchannel, DabComponent, DabService, DabEnsemble,
    SubchannelType, TransmissionMode, ProtectionForm, EEPProfile,
    PROTECTION_LEVEL_TABLE, BITRATE_TABLE
)


class TestProtectionTables:
    """Test protection and bitrate tables."""

    def test_protection_level_table_length(self) -> None:
        """Protection level table should have 64 entries."""
        assert len(PROTECTION_LEVEL_TABLE) == 64

    def test_bitrate_table_length(self) -> None:
        """Bitrate table should have 64 entries."""
        assert len(BITRATE_TABLE) == 64

    def test_bitrate_table_values(self) -> None:
        """Test known bitrate table values."""
        assert BITRATE_TABLE[0] == 32
        assert BITRATE_TABLE[5] == 48
        assert BITRATE_TABLE[61] == 384


class TestDabLabel:
    """Test DAB label class."""

    def test_default_label(self) -> None:
        """Test default label values."""
        label = DabLabel()
        assert label.text == ""
        assert label.short_text == ""
        assert label.flag == 0xFFFF

    def test_label_with_text(self) -> None:
        """Test label with text."""
        label = DabLabel(text="Test Radio", short_text="Test")
        assert label.text == "Test Radio"
        assert label.short_text == "Test"

    def test_to_ebu_latin_length(self) -> None:
        """EBU Latin encoding should be exactly 16 bytes."""
        label = DabLabel(text="Short")
        encoded = label.to_ebu_latin()
        assert len(encoded) == 16

    def test_to_ebu_latin_padding(self) -> None:
        """Short labels should be padded with spaces."""
        label = DabLabel(text="Hi")
        encoded = label.to_ebu_latin()
        assert encoded[:2] == b'Hi'
        assert encoded[2:] == b' ' * 14

    def test_to_ebu_latin_truncation(self) -> None:
        """Long labels should be truncated to 16 bytes."""
        label = DabLabel(text="This is a very long label")
        encoded = label.to_ebu_latin()
        assert len(encoded) == 16

    def test_validate_valid_label(self) -> None:
        """Valid label should pass validation."""
        label = DabLabel(text="Test", short_text="Tst")
        assert label.validate() is True

    def test_validate_long_text(self) -> None:
        """Label with text > 16 chars should fail validation."""
        label = DabLabel(text="This is too long!!!!!")
        assert label.validate() is False

    def test_validate_long_short_text(self) -> None:
        """Label with short_text > 8 chars should fail validation."""
        label = DabLabel(text="Test", short_text="TooLong!!")
        assert label.validate() is False


class TestDabProtection:
    """Test protection configuration."""

    def test_default_protection(self) -> None:
        """Test default protection values."""
        prot = DabProtection()
        assert prot.level == 2
        assert prot.form == ProtectionForm.UEP

    def test_uep_protection(self) -> None:
        """Test UEP protection."""
        uep = DabProtectionUEP(table_index=5)
        prot = DabProtection(level=3, form=ProtectionForm.UEP, uep=uep)
        assert prot.level == 3
        assert prot.form == ProtectionForm.UEP
        assert prot.uep is not None
        assert prot.uep.table_index == 5

    def test_eep_protection(self) -> None:
        """Test EEP protection."""
        eep = DabProtectionEEP(profile=EEPProfile.EEP_A)
        prot = DabProtection(level=2, form=ProtectionForm.EEP, eep=eep)
        assert prot.level == 2
        assert prot.form == ProtectionForm.EEP
        assert prot.eep is not None
        assert prot.eep.profile == EEPProfile.EEP_A

    def test_eep_get_option_a(self) -> None:
        """EEP profile A should return option 0."""
        eep = DabProtectionEEP(profile=EEPProfile.EEP_A)
        assert eep.get_option() == 0

    def test_eep_get_option_b(self) -> None:
        """EEP profile B should return option 1."""
        eep = DabProtectionEEP(profile=EEPProfile.EEP_B)
        assert eep.get_option() == 1

    def test_to_tpl(self) -> None:
        """Test TPL conversion."""
        prot = DabProtection(level=3)
        tpl = prot.to_tpl(bitrate=96)  # 96 kbps bitrate
        assert isinstance(tpl, int)
        assert 0 <= tpl <= 0x3F


class TestDabSubchannel:
    """Test subchannel configuration."""

    def test_default_subchannel(self) -> None:
        """Test default subchannel values."""
        sub = DabSubchannel(uid="audio1")
        assert sub.uid == "audio1"
        assert sub.id == 0
        assert sub.type == SubchannelType.DABAudio
        assert sub.start_address == 0
        assert sub.bitrate == 0

    def test_subchannel_with_values(self) -> None:
        """Test subchannel with specific values."""
        sub = DabSubchannel(
            uid="audio1",
            id=1,
            type=SubchannelType.DABPlusAudio,
            start_address=0,
            bitrate=128
        )
        assert sub.id == 1
        assert sub.type == SubchannelType.DABPlusAudio
        assert sub.bitrate == 128

    def test_get_size_cu(self) -> None:
        """Test capacity unit calculation."""
        sub = DabSubchannel(uid="audio1", bitrate=48)
        sub.protection.level = 5
        size = sub.get_size_cu()
        # Should lookup in table or return 0 if not found
        assert isinstance(size, int)
        assert size >= 0

    def test_get_size_byte(self) -> None:
        """Test byte size calculation."""
        sub = DabSubchannel(uid="audio1", bitrate=48)
        sub.protection.level = 5
        size_cu = sub.get_size_cu()
        size_byte = sub.get_size_byte()
        # Each CU is 4 bytes (1 word = 32 bits)
        assert size_byte == size_cu * 4

    def test_validate_valid_subchannel(self) -> None:
        """Valid subchannel should pass validation."""
        sub = DabSubchannel(uid="audio1", id=5, bitrate=128)
        assert sub.validate() is True

    def test_validate_invalid_id(self) -> None:
        """Subchannel with invalid ID should fail validation."""
        sub = DabSubchannel(uid="audio1", id=64, bitrate=128)
        assert sub.validate() is False

    def test_validate_zero_bitrate(self) -> None:
        """Subchannel with zero bitrate should fail validation."""
        sub = DabSubchannel(uid="audio1", id=5, bitrate=0)
        assert sub.validate() is False


class TestDabComponent:
    """Test component configuration."""

    def test_default_component(self) -> None:
        """Test default component values."""
        comp = DabComponent(uid="comp1")
        assert comp.uid == "comp1"
        assert comp.service_id == 0
        assert comp.subchannel_id == 0
        assert comp.type == 0

    def test_component_with_label(self) -> None:
        """Test component with label."""
        comp = DabComponent(uid="comp1")
        comp.label.text = "Component 1"
        assert comp.label.text == "Component 1"

    def test_validate_valid_component(self) -> None:
        """Valid component should pass validation."""
        comp = DabComponent(uid="comp1")
        comp.label = DabLabel(text="Test", short_text="Tst")
        assert comp.validate() is True

    def test_validate_invalid_label(self) -> None:
        """Component with invalid label should fail validation."""
        comp = DabComponent(uid="comp1")
        comp.label = DabLabel(text="This is way too long for a label")
        assert comp.validate() is False


class TestDabService:
    """Test service configuration."""

    def test_default_service(self) -> None:
        """Test default service values."""
        svc = DabService(uid="svc1")
        assert svc.uid == "svc1"
        assert svc.id == 0
        assert svc.ecc == 0
        assert svc.language == 0

    def test_service_with_values(self) -> None:
        """Test service with specific values."""
        svc = DabService(uid="radio1", id=0x1234)
        svc.label = DabLabel(text="Radio One", short_text="Radio1")
        svc.language = 15  # German
        assert svc.id == 0x1234
        assert svc.label.text == "Radio One"
        assert svc.language == 15

    def test_pty_settings(self) -> None:
        """Test programme type settings."""
        svc = DabService(uid="svc1")
        svc.pty_settings.pty = 5  # Education
        assert svc.pty_settings.pty == 5
        assert svc.pty_settings.dynamic_no_static is False

    def test_validate_valid_service(self) -> None:
        """Valid service should pass validation."""
        svc = DabService(uid="svc1", id=0x1234)
        svc.label = DabLabel(text="Test", short_text="Tst")
        assert svc.validate() is True

    def test_validate_zero_id(self) -> None:
        """Service with zero ID should fail validation."""
        svc = DabService(uid="svc1", id=0)
        svc.label = DabLabel(text="Test")
        assert svc.validate() is False

    def test_validate_invalid_label(self) -> None:
        """Service with invalid label should fail validation."""
        svc = DabService(uid="svc1", id=0x1234)
        svc.label = DabLabel(text="This is way too long!!!!")
        assert svc.validate() is False


class TestDabEnsemble:
    """Test ensemble configuration."""

    def test_default_ensemble(self) -> None:
        """Test default ensemble values."""
        ens = DabEnsemble()
        assert ens.id == 0
        assert ens.ecc == 0
        assert ens.transmission_mode == TransmissionMode.TM_I
        assert len(ens.services) == 0
        assert len(ens.components) == 0
        assert len(ens.subchannels) == 0

    def test_ensemble_with_values(self) -> None:
        """Test ensemble with specific values."""
        ens = DabEnsemble()
        ens.id = 0xABCD
        ens.ecc = 0xE1
        ens.label = DabLabel(text="Test Multiplex", short_text="TestMux")
        ens.transmission_mode = TransmissionMode.TM_I

        assert ens.id == 0xABCD
        assert ens.ecc == 0xE1
        assert ens.label.text == "Test Multiplex"

    def test_add_service(self) -> None:
        """Test adding service to ensemble."""
        ens = DabEnsemble()
        svc = DabService(uid="svc1", id=0x1234)
        ens.services.append(svc)
        assert len(ens.services) == 1

    def test_add_subchannel(self) -> None:
        """Test adding subchannel to ensemble."""
        ens = DabEnsemble()
        sub = DabSubchannel(uid="audio1", id=1, bitrate=128)
        ens.subchannels.append(sub)
        assert len(ens.subchannels) == 1

    def test_get_service(self) -> None:
        """Test getting service by UID."""
        ens = DabEnsemble()
        svc = DabService(uid="radio1", id=0x1234)
        ens.services.append(svc)

        found = ens.get_service("radio1")
        assert found is not None
        assert found.uid == "radio1"

    def test_get_service_not_found(self) -> None:
        """Test getting non-existent service."""
        ens = DabEnsemble()
        found = ens.get_service("nonexistent")
        assert found is None

    def test_get_subchannel(self) -> None:
        """Test getting subchannel by UID."""
        ens = DabEnsemble()
        sub = DabSubchannel(uid="audio1", id=1, bitrate=128)
        ens.subchannels.append(sub)

        found = ens.get_subchannel("audio1")
        assert found is not None
        assert found.uid == "audio1"

    def test_get_component(self) -> None:
        """Test getting component by UID."""
        ens = DabEnsemble()
        comp = DabComponent(uid="comp1")
        ens.components.append(comp)

        found = ens.get_component("comp1")
        assert found is not None
        assert found.uid == "comp1"

    def test_validate_empty_ensemble(self) -> None:
        """Empty ensemble with valid label should pass validation."""
        ens = DabEnsemble()
        ens.label = DabLabel(text="Test")
        assert ens.validate() is True

    def test_validate_ensemble_with_services(self) -> None:
        """Ensemble with valid services should pass validation."""
        ens = DabEnsemble()
        ens.label = DabLabel(text="Test")

        svc = DabService(uid="svc1", id=0x1234)
        svc.label = DabLabel(text="Service")
        ens.services.append(svc)

        assert ens.validate() is True

    def test_validate_ensemble_with_invalid_service(self) -> None:
        """Ensemble with invalid service should fail validation."""
        ens = DabEnsemble()
        ens.label = DabLabel(text="Test")

        # Service with zero ID is invalid
        svc = DabService(uid="svc1", id=0)
        ens.services.append(svc)

        assert ens.validate() is False

    def test_get_total_capacity_units(self) -> None:
        """Test total capacity calculation."""
        ens = DabEnsemble()

        sub1 = DabSubchannel(uid="audio1", bitrate=48)
        sub1.protection.level = 5
        ens.subchannels.append(sub1)

        sub2 = DabSubchannel(uid="audio2", bitrate=48)
        sub2.protection.level = 5
        ens.subchannels.append(sub2)

        total = ens.get_total_capacity_units()
        assert isinstance(total, int)
        assert total >= 0

    def test_lto_configuration(self) -> None:
        """Test local time offset configuration."""
        ens = DabEnsemble()
        assert ens.lto_auto is True
        assert ens.lto == 0

        ens.lto_auto = False
        ens.lto = 2  # +1 hour
        assert ens.lto == 2


class TestTransmissionModes:
    """Test transmission mode enum."""

    def test_transmission_mode_values(self) -> None:
        """Test transmission mode enum values."""
        assert TransmissionMode.TM_I == 1
        assert TransmissionMode.TM_II == 2
        assert TransmissionMode.TM_III == 3
        assert TransmissionMode.TM_IV == 4


class TestSubchannelTypes:
    """Test subchannel type enum."""

    def test_subchannel_types(self) -> None:
        """Test subchannel type enum values."""
        assert SubchannelType.DABAudio.value == "audio"
        assert SubchannelType.DABPlusAudio.value == "dabplus"
        assert SubchannelType.DataDmb.value == "dmb"
        assert SubchannelType.Packet.value == "packet"
