"""
Audio processing module.

This module provides audio frame parsing and validation for MPEG and AAC audio.
"""
from dabmux.audio.mpeg import MpegFrameParser, MpegHeader, MpegLayer, MpegSamplingRate

__all__ = [
    'MpegFrameParser',
    'MpegHeader',
    'MpegLayer',
    'MpegSamplingRate',
]
