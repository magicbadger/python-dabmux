"""
Tests for CLI EDI configuration.

Verifies CLI arguments properly configure EDI output in the ensemble.
"""
import pytest
import socket
import time
from dabmux.cli import DabMuxCLI
from dabmux.core.mux_elements import EdiOutputConfig


class TestCLI_EdiConfiguration:
    """Test EDI configuration via CLI arguments."""

    def test_edi_udp_basic(self, tmp_path):
        """Test basic UDP EDI configuration."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  label:
    text: 'Test'
subchannels: []
services: []
components: []
""")

        cli = DabMuxCLI()
        args = cli.parse_args([
            '-c', str(config_file),
            '--edi', 'udp://192.168.1.100:12000',
            '-n', '1'
        ])

        assert args.edi == 'udp://192.168.1.100:12000'
        assert args.edi_tcp_mode == 'client'  # Default
        assert args.pft is False
        assert args.pft_fec == 0

    def test_edi_tcp_client(self, tmp_path):
        """Test TCP client mode configuration."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  label:
    text: 'Test'
subchannels: []
services: []
components: []
""")

        cli = DabMuxCLI()
        args = cli.parse_args([
            '-c', str(config_file),
            '--edi', 'tcp://192.168.1.100:12000',
            '--edi-tcp-mode', 'client',
            '-n', '1'
        ])

        assert args.edi == 'tcp://192.168.1.100:12000'
        assert args.edi_tcp_mode == 'client'

    def test_edi_tcp_server(self, tmp_path):
        """Test TCP server mode configuration."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  label:
    text: 'Test'
subchannels: []
services: []
components: []
""")

        cli = DabMuxCLI()
        args = cli.parse_args([
            '-c', str(config_file),
            '--edi', 'tcp://0.0.0.0:12000',
            '--edi-tcp-mode', 'server',
            '-n', '1'
        ])

        assert args.edi == 'tcp://0.0.0.0:12000'
        assert args.edi_tcp_mode == 'server'

    def test_edi_pft_enabled(self, tmp_path):
        """Test PFT enablement."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  label:
    text: 'Test'
subchannels: []
services: []
components: []
""")

        cli = DabMuxCLI()
        args = cli.parse_args([
            '-c', str(config_file),
            '--edi', 'udp://239.1.2.3:12000',
            '--pft',
            '--pft-fec', '3',
            '-n', '1'
        ])

        assert args.pft is True
        assert args.pft_fec == 3
        assert args.pft_fragment_size == 1400  # Default

    def test_edi_pft_custom_fragment_size(self, tmp_path):
        """Test custom PFT fragment size."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  label:
    text: 'Test'
subchannels: []
services: []
components: []
""")

        cli = DabMuxCLI()
        args = cli.parse_args([
            '-c', str(config_file),
            '--edi', 'udp://192.168.1.100:12000',
            '--pft',
            '--pft-fragment-size', '1200',
            '-n', '1'
        ])

        assert args.pft is True
        assert args.pft_fragment_size == 1200

    def test_edi_tist_enabled(self, tmp_path):
        """Test TIST timestamp enablement."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  label:
    text: 'Test'
subchannels: []
services: []
components: []
""")

        cli = DabMuxCLI()
        args = cli.parse_args([
            '-c', str(config_file),
            '--edi', 'udp://192.168.1.100:12000',
            '--tist',
            '-n', '1'
        ])

        assert args.tist is True

    def test_edi_source_port(self, tmp_path):
        """Test UDP source port configuration."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  label:
    text: 'Test'
subchannels: []
services: []
components: []
""")

        cli = DabMuxCLI()
        args = cli.parse_args([
            '-c', str(config_file),
            '--edi', 'udp://192.168.1.100:12000',
            '--edi-source-port', '54321',
            '-n', '1'
        ])

        assert args.edi_source_port == 54321

    def test_file_and_edi_combined(self, tmp_path):
        """Test simultaneous file and EDI output."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  label:
    text: 'Test'
subchannels: []
services: []
components: []
""")

        output_file = tmp_path / "output.eti"

        cli = DabMuxCLI()
        args = cli.parse_args([
            '-c', str(config_file),
            '-o', str(output_file),
            '--edi', 'udp://192.168.1.100:12000',
            '-n', '1'
        ])

        assert args.output == str(output_file)
        assert args.edi == 'udp://192.168.1.100:12000'


class TestCLI_EdiEnsembleConfiguration:
    """Test that CLI args properly configure ensemble.edi_output."""

    def test_configure_edi_output_udp(self, tmp_path):
        """Test EDI configuration creates proper EdiOutputConfig for UDP."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  label:
    text: 'Test'
subchannels: []
services: []
components: []
""")

        cli = DabMuxCLI()
        args = cli.parse_args([
            '-c', str(config_file),
            '--edi', 'udp://192.168.1.100:12000',
            '-n', '1'
        ])

        from dabmux.config import load_config
        ensemble = load_config(str(config_file))
        cli.configure_edi_output(args, ensemble)

        assert ensemble.edi_output is not None
        assert ensemble.edi_output.enabled is True
        assert ensemble.edi_output.protocol == 'udp'
        assert ensemble.edi_output.destination == '192.168.1.100:12000'
        assert ensemble.edi_output.enable_pft is False

    def test_configure_edi_output_tcp_client(self, tmp_path):
        """Test EDI configuration creates proper EdiOutputConfig for TCP client."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  label:
    text: 'Test'
subchannels: []
services: []
components: []
""")

        cli = DabMuxCLI()
        args = cli.parse_args([
            '-c', str(config_file),
            '--edi', 'tcp://transmitter.example.com:12000',
            '--edi-tcp-mode', 'client',
            '-n', '1'
        ])

        from dabmux.config import load_config
        ensemble = load_config(str(config_file))
        cli.configure_edi_output(args, ensemble)

        assert ensemble.edi_output is not None
        assert ensemble.edi_output.enabled is True
        assert ensemble.edi_output.protocol == 'tcp'
        assert ensemble.edi_output.destination == 'transmitter.example.com:12000'
        assert ensemble.edi_output.tcp_mode == 'client'

    def test_configure_edi_output_tcp_server(self, tmp_path):
        """Test EDI configuration creates proper EdiOutputConfig for TCP server."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  label:
    text: 'Test'
subchannels: []
services: []
components: []
""")

        cli = DabMuxCLI()
        args = cli.parse_args([
            '-c', str(config_file),
            '--edi', 'tcp://0.0.0.0:12000',
            '--edi-tcp-mode', 'server',
            '-n', '1'
        ])

        from dabmux.config import load_config
        ensemble = load_config(str(config_file))
        cli.configure_edi_output(args, ensemble)

        assert ensemble.edi_output is not None
        assert ensemble.edi_output.protocol == 'tcp'
        assert ensemble.edi_output.tcp_mode == 'server'

    def test_configure_edi_output_pft(self, tmp_path):
        """Test EDI configuration with PFT."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  label:
    text: 'Test'
subchannels: []
services: []
components: []
""")

        cli = DabMuxCLI()
        args = cli.parse_args([
            '-c', str(config_file),
            '--edi', 'udp://239.1.2.3:12000',
            '--pft',
            '--pft-fec', '5',
            '--pft-fragment-size', '1200',
            '-n', '1'
        ])

        from dabmux.config import load_config
        ensemble = load_config(str(config_file))
        cli.configure_edi_output(args, ensemble)

        assert ensemble.edi_output.enable_pft is True
        assert ensemble.edi_output.pft_fec == 5
        assert ensemble.edi_output.pft_fragment_size == 1200

    def test_configure_edi_output_tist(self, tmp_path):
        """Test EDI configuration with TIST."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  label:
    text: 'Test'
subchannels: []
services: []
components: []
""")

        cli = DabMuxCLI()
        args = cli.parse_args([
            '-c', str(config_file),
            '--edi', 'udp://192.168.1.100:12000',
            '--tist',
            '-n', '1'
        ])

        from dabmux.config import load_config
        ensemble = load_config(str(config_file))
        cli.configure_edi_output(args, ensemble)

        assert ensemble.edi_output.enable_tist is True


class TestCLI_EdiValidation:
    """Test CLI validation for EDI arguments."""

    def test_invalid_edi_url_no_protocol(self, tmp_path):
        """Test invalid EDI URL without protocol."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  label:
    text: 'Test'
subchannels: []
services: []
components: []
""")

        cli = DabMuxCLI()
        args = cli.parse_args([
            '-c', str(config_file),
            '--edi', '192.168.1.100:12000',  # Missing protocol
            '-n', '1'
        ])

        from dabmux.config import load_config
        ensemble = load_config(str(config_file))

        with pytest.raises(ValueError, match="Invalid EDI URL"):
            cli.configure_edi_output(args, ensemble)

    def test_invalid_edi_url_no_port(self, tmp_path):
        """Test invalid EDI URL without port."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  label:
    text: 'Test'
subchannels: []
services: []
components: []
""")

        cli = DabMuxCLI()
        args = cli.parse_args([
            '-c', str(config_file),
            '--edi', 'udp://192.168.1.100',  # Missing port
            '-n', '1'
        ])

        from dabmux.config import load_config
        ensemble = load_config(str(config_file))

        with pytest.raises(ValueError, match="must include port"):
            cli.configure_edi_output(args, ensemble)

    def test_no_output_configured_error(self, tmp_path):
        """Test error when no output is configured."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  label:
    text: 'Test'
subchannels: []
services: []
components: []
""")

        cli = DabMuxCLI()

        # Running without -o or --edi should return error code
        exit_code = cli.run(['-c', str(config_file)])
        assert exit_code == 1  # Error exit code
