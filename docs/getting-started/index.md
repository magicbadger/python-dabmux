# Getting Started with python-dabmux

Welcome! This guide will help you get python-dabmux installed and create your first DAB multiplex in under 15 minutes.

## What You'll Learn

This getting started guide offers two paths:

### ⚡ Fast Track (5 minutes)

**[Quick Setup: Audio to Stream](quick-setup.md)** - Minimal steps to get a multiplex running NOW

- Create audio file
- Write 10-line config
- Run and verify
- Perfect for: "I just want to see it work!"

### 📚 Detailed Path (15 minutes)

1. **[Installation](installation.md)**: Install python-dabmux and its dependencies
2. **[Your First Multiplex](first-multiplex.md)**: Create and run a basic DAB ensemble with explanations
3. **[Basic Concepts](basic-concepts.md)**: Understand DAB terminology and architecture

## Prerequisites

Before you begin, make sure you have:

- **Python 3.11 or later**: python-dabmux requires Python 3.11+
- **Basic command-line knowledge**: You'll run commands in a terminal
- **Audio files**: MPEG Layer II files for testing (optional - we provide examples)

## What is a DAB Multiplexer?

A DAB multiplexer combines multiple audio streams (radio stations) into a single DAB ensemble for transmission. Think of it like this:

```
┌─────────────┐
│ Radio One   │─┐
├─────────────┤ │
│ Radio Two   │─┼─→ ┌──────────────┐      ┌────────────┐
├─────────────┤ │   │ Multiplexer  │─────→│ ETI Output │
│ Radio Three │─┘   └──────────────┘      └────────────┘
└─────────────┘
  Audio Streams        Combines into          DAB Signal
                       DAB Ensemble
```

The multiplexer:

- Reads audio from multiple sources (files, network streams)
- Adds metadata (station names, programme types, etc.)
- Generates Fast Information Groups (FIGs) with service information
- Combines everything into ETI (Ensemble Transport Interface) frames
- Outputs ETI files or EDI network streams for transmission

## Quick Start Path

Follow this path to get up and running:

1. **[Install python-dabmux](installation.md)** (5 minutes)
   - Set up a Python virtual environment
   - Install python-dabmux with pip
   - Verify the installation

2. **[Create Your First Multiplex](first-multiplex.md)** (10 minutes)
   - Write a simple configuration file
   - Run the multiplexer
   - Verify the output

3. **[Learn Basic Concepts](basic-concepts.md)** (optional reading)
   - Understand DAB terminology
   - Learn about ensembles, services, and subchannels
   - Explore the configuration hierarchy

## After Getting Started

Once you've completed this guide, explore:

- **[Configuration Reference](../user-guide/configuration/index.md)**: Learn all configuration options
- **[Tutorials](../tutorials/index.md)**: Hands-on guides for specific scenarios
- **[Architecture](../architecture/index.md)**: Understand how python-dabmux works internally

## Need Help?

If you run into issues:

- Check the **[Troubleshooting Guide](../troubleshooting/index.md)** for common errors
- Read the **[FAQ](../faq.md)** for frequently asked questions
- Report bugs on [GitHub Issues](https://github.com/python-dabmux/python-dabmux/issues)

---

Ready? Let's start with [Installation →](installation.md)
