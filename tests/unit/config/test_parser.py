"""
Unit tests for configuration parser.
"""
import pytest
import tempfile
from pathlib import Path
from dabmux.config.parser import ConfigParser, create_example_config
from dabmux.core.mux_elements import TransmissionMode, SubchannelType


class TestConfigParser:
    """Test configuration parser."""

    def test_parse_minimal_config(self) -> None:
        """Test parsing minimal configuration."""
        config = {
            'ensemble': {
                'id': '0xCE15',
                'ecc': '0xE1',
                'label': 'Test'
            }
        }

        ensemble = ConfigParser.parse_dict(config)
        assert ensemble.id == 0xCE15
        assert ensemble.ecc == 0xE1
        assert ensemble.label.text == 'Test'

    def test_parse_full_config(self) -> None:
        """Test parsing full configuration."""
        config = create_example_config()
        ensemble = ConfigParser.parse_dict(config)

        assert ensemble.id == 0xCE15
        assert ensemble.ecc == 0xE1
        assert ensemble.transmission_mode == TransmissionMode.TM_I
        assert len(ensemble.subchannels) == 1
        assert len(ensemble.services) == 1
        assert len(ensemble.components) == 1

    def test_parse_hex_ids(self) -> None:
        """Test parsing hexadecimal IDs."""
        config = {
            'ensemble': {
                'id': '0xABCD',
                'ecc': '0x12',
                'label': 'Test'
            }
        }

        ensemble = ConfigParser.parse_dict(config)
        assert ensemble.id == 0xABCD
        assert ensemble.ecc == 0x12

    def test_parse_decimal_ids(self) -> None:
        """Test parsing decimal IDs."""
        config = {
            'ensemble': {
                'id': '12345',
                'ecc': '200',
                'label': 'Test'
            }
        }

        ensemble = ConfigParser.parse_dict(config)
        assert ensemble.id == 12345
        assert ensemble.ecc == 200

    def test_parse_transmission_modes(self) -> None:
        """Test parsing different transmission modes."""
        modes = [
            ('I', TransmissionMode.TM_I),
            ('II', TransmissionMode.TM_II),
            ('III', TransmissionMode.TM_III),
            ('IV', TransmissionMode.TM_IV),
            ('1', TransmissionMode.TM_I),
            ('2', TransmissionMode.TM_II)
        ]

        for mode_str, expected in modes:
            config = {
                'ensemble': {
                    'id': '0xCE15',
                    'transmission_mode': mode_str,
                    'label': 'Test'
                }
            }
            ensemble = ConfigParser.parse_dict(config)
            assert ensemble.transmission_mode == expected

    def test_parse_label_string(self) -> None:
        """Test parsing label as string."""
        config = {
            'ensemble': {
                'id': '0xCE15',
                'label': 'Simple Label'
            }
        }

        ensemble = ConfigParser.parse_dict(config)
        assert ensemble.label.text == 'Simple Label'
        assert ensemble.label.short_text == ''

    def test_parse_label_dict(self) -> None:
        """Test parsing label as dictionary."""
        config = {
            'ensemble': {
                'id': '0xCE15',
                'label': {
                    'text': 'Full Label',
                    'short': 'Short'
                }
            }
        }

        ensemble = ConfigParser.parse_dict(config)
        assert ensemble.label.text == 'Full Label'
        assert ensemble.label.short_text == 'Short'

    def test_parse_subchannel(self) -> None:
        """Test parsing subchannel."""
        config = {
            'ensemble': {
                'id': '0xCE15',
                'label': 'Test'
            },
            'subchannels': [
                {
                    'uid': 'audio1',
                    'id': 0,
                    'type': 'audio',
                    'bitrate': 128,
                    'start_address': 0,
                    'protection': 2,
                    'input': 'file://test.mp2'
                }
            ]
        }

        ensemble = ConfigParser.parse_dict(config)
        assert len(ensemble.subchannels) == 1

        sub = ensemble.subchannels[0]
        assert sub.uid == 'audio1'
        assert sub.id == 0
        assert sub.type == SubchannelType.DABAudio
        assert sub.bitrate == 128
        assert sub.start_address == 0
        assert sub.protection.level == 2
        assert sub.input_uri == 'file://test.mp2'

    def test_parse_subchannel_types(self) -> None:
        """Test parsing different subchannel types."""
        types = [
            ('audio', SubchannelType.DABAudio),
            ('dab', SubchannelType.DABAudio),
            ('dabplus', SubchannelType.DABPlusAudio),
            ('dab+', SubchannelType.DABPlusAudio),
            ('packet', SubchannelType.Packet),
            ('data', SubchannelType.Packet)
        ]

        for type_str, expected in types:
            config = {
                'ensemble': {
                    'id': '0xCE15',
                    'label': 'Test'
                },
                'subchannels': [
                    {
                        'uid': 'test',
                        'type': type_str,
                        'bitrate': 128
                    }
                ]
            }
            ensemble = ConfigParser.parse_dict(config)
            assert ensemble.subchannels[0].type == expected

    def test_parse_service(self) -> None:
        """Test parsing service."""
        config = {
            'ensemble': {
                'id': '0xCE15',
                'label': 'Test'
            },
            'services': [
                {
                    'uid': 'service1',
                    'id': '0x5001',
                    'label': 'Radio One',
                    'pty': 1,
                    'language': 9
                }
            ]
        }

        ensemble = ConfigParser.parse_dict(config)
        assert len(ensemble.services) == 1

        svc = ensemble.services[0]
        assert svc.uid == 'service1'
        assert svc.id == 0x5001
        assert svc.label.text == 'Radio One'
        assert svc.pty_settings.pty == 1
        assert svc.language == 9

    def test_parse_component(self) -> None:
        """Test parsing component."""
        config = {
            'ensemble': {
                'id': '0xCE15',
                'label': 'Test'
            },
            'components': [
                {
                    'uid': 'comp1',
                    'service_id': '0x5001',
                    'subchannel_id': 0,
                    'type': 0
                }
            ]
        }

        ensemble = ConfigParser.parse_dict(config)
        assert len(ensemble.components) == 1

        comp = ensemble.components[0]
        assert comp.uid == 'comp1'
        assert comp.service_id == 0x5001
        assert comp.subchannel_id == 0
        assert comp.type == 0

    def test_parse_missing_ensemble(self) -> None:
        """Test that missing ensemble section raises error."""
        config = {}
        with pytest.raises(ValueError, match="Missing 'ensemble'"):
            ConfigParser.parse_dict(config)

    def test_parse_file(self, tmp_path: Path) -> None:
        """Test parsing from file."""
        # Create temporary config file
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("""
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  label: 'Test Ensemble'
""")

        ensemble = ConfigParser.parse_file(str(config_file))
        assert ensemble.id == 0xCE15
        assert ensemble.label.text == 'Test Ensemble'

    def test_parse_file_not_found(self) -> None:
        """Test that non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            ConfigParser.parse_file('/nonexistent/config.yaml')


class TestCreateExampleConfig:
    """Test example configuration creation."""

    def test_create_example(self) -> None:
        """Test creating example configuration."""
        config = create_example_config()

        assert 'ensemble' in config
        assert 'subchannels' in config
        assert 'services' in config
        assert 'components' in config

    def test_parse_example_config(self) -> None:
        """Test that example config can be parsed."""
        config = create_example_config()
        ensemble = ConfigParser.parse_dict(config)

        # Check that all required elements are present
        assert ensemble.id > 0
        assert len(ensemble.label.text) > 0
        assert len(ensemble.subchannels) > 0
        assert len(ensemble.services) > 0
        assert len(ensemble.components) > 0
