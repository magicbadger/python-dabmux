# User Guide

Complete guide to using python-dabmux for DAB/DAB+ multiplexing.

## Overview

This user guide covers everything you need to operate python-dabmux effectively:

- **[CLI Reference](cli-reference.md)**: Complete command-line interface documentation
- **[Configuration](configuration/index.md)**: YAML configuration file reference
- **[Inputs](inputs/index.md)**: File and network input sources
- **[Outputs](outputs/index.md)**: ETI files and EDI network output

## Quick Navigation

### Configuration

- [Configuration Overview](configuration/index.md)
- [Ensemble Parameters](configuration/ensemble.md)
- [Services](configuration/services.md)
- [Subchannels](configuration/subchannels.md)
- [Protection Levels](configuration/protection.md)
- [Configuration Examples](configuration/examples.md)

### Inputs

- [Input Overview](inputs/index.md)
- [File Inputs](inputs/file-inputs.md)
- [Network Inputs](inputs/network-inputs.md)
- [Audio Formats](inputs/audio-formats.md)

### Outputs

- [Output Overview](outputs/index.md)
- [ETI Files](outputs/eti-files.md)
- [EDI Network](outputs/edi-network.md)
- [PFT Fragmentation](outputs/pft-fragmentation.md)

## Common Tasks

### Creating a Multiplex

1. [Write a configuration file](configuration/index.md)
2. [Prepare audio inputs](inputs/file-inputs.md)
3. [Run the multiplexer](cli-reference.md)
4. [Verify the output](outputs/eti-files.md)

### Streaming Over Network

1. [Configure network inputs](inputs/network-inputs.md)
2. [Enable EDI output](outputs/edi-network.md)
3. [Add PFT for reliability](outputs/pft-fragmentation.md)
4. [Run continuously](cli-reference.md#continuous)

### Troubleshooting

- [Common Errors](../troubleshooting/common-errors.md)
- [Input Issues](../troubleshooting/input-issues.md)
- [Output Issues](../troubleshooting/output-issues.md)
- [Network Issues](../troubleshooting/network-issues.md)

## See Also

- [Getting Started](../getting-started/index.md): Installation and first multiplex
- [Tutorials](../tutorials/index.md): Hands-on guides
- [Architecture](../architecture/index.md): System design
- [API Reference](../api-reference/index.md): Python API documentation
