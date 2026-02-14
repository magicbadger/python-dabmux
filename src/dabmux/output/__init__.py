"""
Output abstractions for DAB multiplexing.

This module provides abstract base classes and implementations for writing
ETI frames to various destinations (files, network, etc.).
"""
from dabmux.output.base import DabOutput
from dabmux.output.file import FileOutput, EtiFileType

__all__ = [
    'DabOutput',
    'FileOutput',
    'EtiFileType',
]
