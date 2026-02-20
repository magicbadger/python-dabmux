"""
Configuration file parser for DAB multiplexer.

Supports YAML configuration files for defining ensembles, services, and subchannels.
"""
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from dabmux.core.mux_elements import (
    DabEnsemble,
    DabService,
    DabComponent,
    DabSubchannel,
    DabLabel,
    DabProtection,
    PADConfig,
    DLSConfig,
    PtySettings,
    DateTimeConfig,
    AnnouncementConfig,
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

        # Parse ensemble label (handle both inline and separate short_label)
        label_config = ensemble_config.get('label', {})
        if isinstance(label_config, str) and 'short_label' in ensemble_config:
            # Inline label string with separate short_label key
            label = DabLabel(
                text=label_config,
                short_text=ensemble_config.get('short_label', '')
            )
            if label.short_text:
                label.flag = ConfigParser._calculate_short_label_flag(label.text, label.short_text)
        else:
            # Use standard label parsing
            label = ConfigParser._parse_label(label_config)

        # Parse datetime configuration
        datetime_config = DateTimeConfig()
        if 'datetime' in ensemble_config:
            dt_dict = ensemble_config['datetime']
            datetime_config.enabled = dt_dict.get('enabled', False)
            datetime_config.source = dt_dict.get('source', 'system')
            datetime_config.include_lto = dt_dict.get('include_lto', True)
            datetime_config.utc_flag = dt_dict.get('utc_flag', True)
            datetime_config.confidence = dt_dict.get('confidence', True)

        # Create ensemble
        ensemble = DabEnsemble(
            id=ens_id,
            ecc=ecc,
            label=label,
            transmission_mode=transmission_mode,
            lto_auto=ensemble_config.get('lto_auto', True),
            lto=ensemble_config.get('lto', 0),
            international_table=ensemble_config.get('international_table', 1),
            datetime=datetime_config
        )

        # Parse subchannels
        if 'subchannels' in config:
            for sub_config in config['subchannels']:
                subchannel = ConfigParser._parse_subchannel(sub_config)
                ensemble.subchannels.append(subchannel)

        # Auto-assign subchannel IDs and calculate start addresses
        current_address = 0
        for idx, subchannel in enumerate(ensemble.subchannels):
            # Assign sequential ID if not explicitly set
            if subchannel.id == 0 and idx > 0:
                subchannel.id = idx

            # Calculate start address (cumulative from previous subchannels)
            subchannel.start_address = current_address

            # Calculate size in CUs for this subchannel
            size_cu = subchannel.get_size_cu()
            current_address += size_cu

        # Parse services (and track subchannel references for auto-component creation)
        service_subchannel_map = {}  # Map service ID → subchannel UID
        if 'services' in config:
            for svc_config in config['services']:
                service = ConfigParser._parse_service(svc_config)
                ensemble.services.append(service)

                # Track subchannel reference for auto-component creation
                if 'subchannel' in svc_config:
                    service_subchannel_map[service.id] = svc_config['subchannel']

        # Parse components
        if 'components' in config:
            for comp_config in config['components']:
                component = ConfigParser._parse_component(comp_config)
                ensemble.components.append(component)

        # Auto-create components from service→subchannel references
        # (if no explicit components were defined)
        if not config.get('components') and service_subchannel_map:
            for service_id, subchannel_uid in service_subchannel_map.items():
                # Find subchannel by UID
                subchannel = next((sc for sc in ensemble.subchannels if sc.uid == subchannel_uid), None)
                if subchannel:
                    # Determine Audio Service Component Type (ASCTy)
                    # Per ETSI EN 300 401 Table 9:
                    # 0 = MPEG-1 Layer II (DAB)
                    # 63 = MPEG-4 HE-AAC v2 (DAB+)
                    ascty = 63 if subchannel.type == SubchannelType.DABPlusAudio else 0

                    # Create component linking service to subchannel
                    component = DabComponent(
                        uid=f"comp_{service_id:04X}_{subchannel.id}",
                        service_id=service_id,
                        subchannel_id=subchannel.id,
                        label=DabLabel(),  # Empty label
                        type=ascty
                    )
                    ensemble.components.append(component)

        return ensemble

    @staticmethod
    def _parse_label(label_config: Any) -> DabLabel:
        """Parse label configuration."""
        if isinstance(label_config, str):
            label = DabLabel(text=label_config, short_text="")
        elif isinstance(label_config, dict):
            label = DabLabel(
                text=label_config.get('text', ''),
                short_text=label_config.get('short', label_config.get('short_text', ''))
            )
        else:
            label = DabLabel(text='', short_text='')

        # Calculate short label flag if short text is provided
        if label.short_text:
            label.flag = ConfigParser._calculate_short_label_flag(label.text, label.short_text)

        return label

    @staticmethod
    def _calculate_short_label_flag(long_label: str, short_label: str) -> int:
        """
        Calculate short label flag (16-bit mask).

        Each bit indicates if that character from the long label
        is part of the short label. Most significant bit = first character.

        Args:
            long_label: Full label (up to 16 chars)
            short_label: Short label (up to 8 chars)

        Returns:
            16-bit flag mask
        """
        if not short_label or not long_label:
            return 0xFFFF  # Default: use all characters

        # Pad long label to 16 characters for comparison
        long_padded = long_label.ljust(16)

        # Find consecutive characters that form the short label
        flag = 0
        short_idx = 0
        for i in range(16):
            if short_idx < len(short_label) and i < len(long_label):
                if long_padded[i] == short_label[short_idx]:
                    flag |= (1 << (15 - i))  # Set bit (MSB first)
                    short_idx += 1

        return flag if flag != 0 else 0xFFFF

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

        # Auto-detect type from input URI if type is default 'audio'
        if type_str == 'audio' and 'input_uri' in sub_config:
            input_uri = sub_config['input_uri'].lower()
            # DAB+ file extensions (pre-encoded AAC)
            if input_uri.endswith(('.aac', '.dabp', '.dabplus')):
                subchannel_type = SubchannelType.DABPlusAudio
            # DAB file extensions (MPEG-2 Layer II)
            elif input_uri.endswith(('.mp2', '.mpa')):
                subchannel_type = SubchannelType.DABAudio

        # Parse protection
        from dabmux.core.mux_elements import ProtectionForm, DabProtectionEEP, EEPProfile, DabProtectionUEP
        protection = DabProtection()
        if 'protection' in sub_config:
            prot_config = sub_config['protection']
            if isinstance(prot_config, dict):
                protection.level = prot_config.get('level', 2)
                shortform = prot_config.get('shortform', True)
                if not shortform:
                    # Long form = EEP
                    protection.form = ProtectionForm.EEP
                    protection.eep = DabProtectionEEP(profile=EEPProfile.EEP_A)
            elif isinstance(prot_config, str):
                # Parse protection string (e.g., "EEP_3A", "UEP_2")
                prot_str = prot_config.upper().replace('-', '_')
                if prot_str.startswith('EEP_'):
                    # EEP format: "EEP_<level><profile>" e.g., "EEP_3A", "EEP_2B"
                    protection.form = ProtectionForm.EEP
                    parts = prot_str[4:]  # Remove "EEP_" prefix
                    if parts:
                        # Extract level (first digit)
                        level = int(parts[0]) if parts[0].isdigit() else 2
                        # Extract profile (A or B), default to A
                        profile_char = parts[1] if len(parts) > 1 and parts[1] in ['A', 'B'] else 'A'
                        protection.level = level - 1  # Convert 1-5 to 0-4
                        profile = EEPProfile.EEP_A if profile_char == 'A' else EEPProfile.EEP_B
                        protection.eep = DabProtectionEEP(profile=profile)
                elif prot_str.startswith('UEP_'):
                    # UEP format: "UEP_<level>" e.g., "UEP_2", "UEP_3"
                    protection.form = ProtectionForm.UEP
                    parts = prot_str[4:]  # Remove "UEP_" prefix
                    if parts and parts[0].isdigit():
                        protection.level = int(parts[0]) - 1  # Convert 1-5 to 0-4
                    protection.uep = DabProtectionUEP()
            elif isinstance(prot_config, int):
                protection.level = prot_config

        # Parse PAD configuration
        pad_config = None
        if 'pad' in sub_config:
            pad_config = ConfigParser._parse_pad(sub_config['pad'])

        return DabSubchannel(
            uid=sub_config.get('uid', sub_config.get('id', 'unknown')),
            id=sub_config.get('id', 0) if isinstance(sub_config.get('id'), int) else 0,
            type=subchannel_type,
            start_address=sub_config.get('start_address', sub_config.get('address', 0)),
            bitrate=sub_config.get('bitrate', 128),
            protection=protection,
            input_uri=sub_config.get('input', sub_config.get('input_uri', '')),
            pad=pad_config
        )

    @staticmethod
    def _parse_pad(pad_dict: Dict[str, Any]) -> Optional[PADConfig]:
        """
        Parse PAD configuration.

        Args:
            pad_dict: PAD configuration dictionary from YAML

        Returns:
            PADConfig or None if PAD disabled
        """
        if not pad_dict.get('enabled', False):
            return None

        # Parse DLS configuration
        dls_config = None
        if 'dls' in pad_dict:
            dls_dict = pad_dict['dls']
            if dls_dict.get('enabled', False):
                dls_config = DLSConfig(
                    enabled=True,
                    input_type=dls_dict.get('input_type', 'file'),
                    input_path=dls_dict.get('input_path', dls_dict.get('input', '')),
                    charset=dls_dict.get('charset', 'utf8'),
                    default_label=dls_dict.get('label', dls_dict.get('default_label', '')),
                    poll_interval=float(dls_dict.get('poll_interval', 1.0))
                )

        return PADConfig(
            enabled=True,
            length=pad_dict.get('length', 58),
            dls=dls_config
        )

    @staticmethod
    def _parse_service(svc_config: Dict[str, Any]) -> DabService:
        """Parse service configuration."""
        # Parse service ID (support both 'id' and 'sid')
        svc_id = svc_config.get('sid', svc_config.get('id', 0))
        if isinstance(svc_id, str):
            svc_id = int(svc_id, 16) if svc_id.startswith('0x') else int(svc_id)

        # Parse PTy settings
        pty_settings = PtySettings()
        if 'pty' in svc_config:
            pty_settings.pty = svc_config['pty']

        # Parse service label (handle both inline and separate short_label)
        label_config = svc_config.get('label', {})
        if isinstance(label_config, str) and 'short_label' in svc_config:
            # Inline label string with separate short_label key
            label = DabLabel(
                text=label_config,
                short_text=svc_config.get('short_label', '')
            )
            if label.short_text:
                label.flag = ConfigParser._calculate_short_label_flag(label.text, label.short_text)
        else:
            # Use standard label parsing
            label = ConfigParser._parse_label(label_config)

        # Parse announcement configuration
        ann_config = AnnouncementConfig()
        if 'announcements' in svc_config:
            ann_dict = svc_config['announcements']
            ann_config.enabled = ann_dict.get('enabled', False)
            ann_config.types = ann_dict.get('types', [])
            ann_config.new_flag = ann_dict.get('new_flag', False)
            ann_config.region_flag = ann_dict.get('region_flag', False)

        # Parse clusters (can be in announcements or at service level)
        clusters = svc_config.get('clusters', [])
        if 'announcements' in svc_config:
            clusters = svc_config['announcements'].get('clusters', clusters)

        return DabService(
            uid=svc_config.get('uid', f"service_{svc_id}"),
            id=svc_id,
            ecc=svc_config.get('ecc', 0),
            label=label,
            pty_settings=pty_settings,
            language=svc_config.get('language', 0),
            asu=svc_config.get('asu', 0),
            clusters=clusters,
            announcements=ann_config
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
