"""
Input abstractions for DAB multiplexing.

This module provides abstract base classes and implementations for reading
audio/data from various sources (files, network, etc.).
"""
# Legacy input classes (for DAB MPEG and raw data)
from dabmux.input.base import InputBase, BufferManagement
from dabmux.input.file import FileInput, MPEGFileInput, RawFileInput

# DAB+ input classes (for pre-encoded streams from ODR-AudioEnc)
from dabmux.input.dabplus_input import DABPlusInput
from dabmux.input.dabplus_file import DABPlusFileInput
from dabmux.input.dabplus_fifo import DABPlusFifoInput
from dabmux.input.dabplus_udp import DABPlusUdpInput
from dabmux.input.dabplus_factory import DABPlusInputFactory

# Unified factory (recommended for all new code)
from dabmux.input.factory import InputFactory

__all__ = [
    # Legacy classes
    'InputBase',
    'BufferManagement',
    'FileInput',
    'MPEGFileInput',
    'RawFileInput',
    # DAB+ classes
    'DABPlusInput',
    'DABPlusFileInput',
    'DABPlusFifoInput',
    'DABPlusUdpInput',
    'DABPlusInputFactory',
    # Unified factory (recommended)
    'InputFactory',
]
