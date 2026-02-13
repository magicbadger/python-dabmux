"""
Configuration file parser for DAB multiplexer.

Supports YAML configuration files for defining ensembles, services, and subchannels.
"""
import yaml
from pathlib import Path
from typing import Dict, Any, List
from dabmux.core.mux_elements import (
    DabEnsemble,
    DabService,
    DabComponent,
    DabSubchannel,
    DabLabel,
    DabProtection,
    PtySettings,
    SubchannelType,
    TransmissionMode
)


class ConfigParser:
    """
    Parse YAML configuration files for DAB multiplexer.
    """

    @staticmethod
    def parse_file(config_path: str) -> DabEnsemble:
        """
        Parse configuration file and create ensemble.

        Args:
            config_path: Path to YAML configuration file

        Returns:
            Configured DabEnsemble

        Raises:
            ValueError: If configuration is invalid
            FileNotFoundError: If config file doesn't exist
        """
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(path, 'r') as f:
            config = yaml.safe_load(f)

        return ConfigParser.parse_dict(config)

    @staticmethod
    def parse_dict(config: Dict[str, Any]) -> DabEnsemble:
        """
        Parse configuration dictionary and create ensemble.

        Args:
            config: Configuration dictionary

        Returns:
            Configured DabEnsemble

        Raises:
            ValueError: If configuration is invalid
        """
        if 'ensemble' not in config:
            raise ValueError("Missing 'ensemble' section in configuration")

        ensemble_config = config['ensemble']

        # Parse ensemble parameters
        ens_id = ensemble_config.get('id', 0)
        if isinstance(ens_id, str):
            ens_id = int(ens_id, 16) if ens_id.startswith('0x') else int(ens_id)

        ecc = ensemble_config.get('ecc', 0xE1)
        if isinstance(ecc, str):
            ecc = int(ecc, 16) if ecc.startswith('0x') else int(ecc)

        # Parse transmission mode
        mode_str = ensemble_config.get('transmission_mode', 'I')
        mode_map = {'I': TransmissionMode.TM_I, 'II': TransmissionMode.TM_II,
                    'III': TransmissionMode.TM_III, 'IV': TransmissionMode.TM_IV,
                    '1': TransmissionMode.TM_I, '2': TransmissionMode.TM_II,
                    '3': TransmissionMode.TM_III, '4': TransmissionMode.TM_IV}
        transmission_mode = mode_map.get(mode_str.upper(), TransmissionMode.TM_I)

        # Create ensemble
        ensemble = DabEnsemble(
            id=ens_id,
            ecc=ecc,
            label=ConfigParser._parse_label(ensemble_config.get('label', {})),
            transmission_mode=transmission_mode,
            lto_auto=ensemble_config.get('lto_auto', True),
            lto=ensemble_config.get('lto', 0)
        )

        # Parse subchannels
        if 'subchannels' in config:
            for sub_config in config['subchannels']:
                subchannel = ConfigParser._parse_subchannel(sub_config)
                ensemble.subchannels.append(subchannel)

        # Parse services
        if 'services' in config:
            for svc_config in config['services']:
                service = ConfigParser._parse_service(svc_config)
                ensemble.services.append(service)

        # Parse components
        if 'components' in config:
            for comp_config in config['components']:
                component = ConfigParser._parse_component(comp_config)
                ensemble.components.append(component)

        return ensemble

    @staticmethod
    def _parse_label(label_config: Any) -> DabLabel:
        """Parse label configuration."""
        if isinstance(label_config, str):
            return DabLabel(text=label_config, short_text="")
        elif isinstance(label_config, dict):
            return DabLabel(
                text=label_config.get('text', ''),
                short_text=label_config.get('short', label_config.get('short_text', ''))
            )
        else:
            return DabLabel(text='', short_text='')

    @staticmethod
    def _parse_subchannel(sub_config: Dict[str, Any]) -> DabSubchannel:
        """Parse subchannel configuration."""
        # Parse subchannel type
        type_str = sub_config.get('type', 'audio').lower()
        type_map = {
            'audio': SubchannelType.DABAudio,
            'dab': SubchannelType.DABAudio,
            'dabplus': SubchannelType.DABPlusAudio,
            'dab+': SubchannelType.DABPlusAudio,
            'packet': SubchannelType.Packet,
            'data': SubchannelType.Packet,
            'dmb': SubchannelType.DataDmb
        }
        subchannel_type = type_map.get(type_str, SubchannelType.DABAudio)

        # Parse protection
        protection = DabProtection()
        if 'protection' in sub_config:
            prot_config = sub_config['protection']
            if isinstance(prot_config, dict):
                protection.level = prot_config.get('level', 2)
                protection.shortform = prot_config.get('shortform', True)
            elif isinstance(prot_config, int):
                protection.level = prot_config

        return DabSubchannel(
            uid=sub_config.get('uid', sub_config.get('id', 'unknown')),
            id=sub_config.get('id', 0) if isinstance(sub_config.get('id'), int) else 0,
            type=subchannel_type,
            start_address=sub_config.get('start_address', sub_config.get('address', 0)),
            bitrate=sub_config.get('bitrate', 128),
            protection=protection,
            input_uri=sub_config.get('input', sub_config.get('input_uri', ''))
        )

    @staticmethod
    def _parse_service(svc_config: Dict[str, Any]) -> DabService:
        """Parse service configuration."""
        # Parse service ID
        svc_id = svc_config.get('id', 0)
        if isinstance(svc_id, str):
            svc_id = int(svc_id, 16) if svc_id.startswith('0x') else int(svc_id)

        # Parse PTy settings
        pty_settings = PtySettings()
        if 'pty' in svc_config:
            pty_settings.pty = svc_config['pty']

        return DabService(
            uid=svc_config.get('uid', f"service_{svc_id}"),
            id=svc_id,
            label=ConfigParser._parse_label(svc_config.get('label', {})),
            pty_settings=pty_settings,
            language=svc_config.get('language', 0)
        )

    @staticmethod
    def _parse_component(comp_config: Dict[str, Any]) -> DabComponent:
        """Parse component configuration."""
        # Parse service and subchannel IDs
        service_id = comp_config.get('service_id', comp_config.get('service', 0))
        if isinstance(service_id, str):
            service_id = int(service_id, 16) if service_id.startswith('0x') else int(service_id)

        subchannel_id = comp_config.get('subchannel_id', comp_config.get('subchannel', 0))

        return DabComponent(
            uid=comp_config.get('uid', f"component_{service_id}_{subchannel_id}"),
            service_id=service_id,
            subchannel_id=subchannel_id,
            label=ConfigParser._parse_label(comp_config.get('label', {})),
            type=comp_config.get('type', 0)
        )


def load_config(config_path: str) -> DabEnsemble:
    """
    Load configuration from file.

    Args:
        config_path: Path to configuration file

    Returns:
        Configured DabEnsemble
    """
    return ConfigParser.parse_file(config_path)


def create_example_config() -> Dict[str, Any]:
    """
    Create an example configuration dictionary.

    Returns:
        Example configuration
    """
    return {
        'ensemble': {
            'id': '0xCE15',
            'ecc': '0xE1',
            'transmission_mode': 'I',
            'label': {
                'text': 'Test Ensemble',
                'short': 'Test'
            },
            'lto_auto': True
        },
        'subchannels': [
            {
                'uid': 'audio1',
                'id': 0,
                'type': 'audio',
                'bitrate': 128,
                'start_address': 0,
                'protection': {
                    'level': 2,
                    'shortform': True
                },
                'input': 'file://audio.mp2'
            }
        ],
        'services': [
            {
                'uid': 'service1',
                'id': '0x5001',
                'label': {
                    'text': 'Radio One',
                    'short': 'Radio1'
                },
                'pty': 1,  # News
                'language': 9  # English
            }
        ],
        'components': [
            {
                'uid': 'comp1',
                'service_id': '0x5001',
                'subchannel_id': 0,
                'type': 0  # Audio
            }
        ]
    }
