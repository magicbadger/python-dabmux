# Tutorials

Hands-on tutorials for common python-dabmux scenarios. Each tutorial walks you through a complete setup from start to finish.

## Available Tutorials

### [Basic Single Service](basic-single-service.md)

**Difficulty:** Beginner
**Time:** 15 minutes

Create your first DAB multiplex with a single radio station. Perfect for getting started.

**You'll learn:**
- How to write a minimal configuration
- Running the multiplexer
- Verifying ETI output
- Testing with different audio files

[Start Tutorial →](basic-single-service.md)

---

### [Multi-Service Ensemble](multi-service-ensemble.md)

**Difficulty:** Intermediate
**Time:** 25 minutes

Build a complete DAB ensemble with multiple radio stations, mixing DAB and DAB+ services.

**You'll learn:**
- Managing multiple services
- Calculating capacity allocation
- Organizing subchannels
- Service labels and metadata

[Start Tutorial →](multi-service-ensemble.md)

---

### [DAB+ Setup](dab-plus-setup.md)

**Difficulty:** Intermediate
**Time:** 20 minutes

Set up DAB+ (HE-AAC v2) services for more efficient broadcasting.

**You'll learn:**
- Converting audio to HE-AAC
- DAB+ configuration
- Bitrate optimization
- Quality vs. capacity trade-offs

[Start Tutorial →](dab-plus-setup.md)

---

### [Network Streaming](network-streaming.md)

**Difficulty:** Intermediate
**Time:** 30 minutes

Stream audio over the network using UDP and TCP inputs for live broadcasting.

**You'll learn:**
- Setting up UDP network inputs
- Using TCP for reliable streaming
- Live audio encoding with ffmpeg
- Handling network issues

[Start Tutorial →](network-streaming.md)

---

### [PFT with FEC](pft-with-fec.md)

**Difficulty:** Advanced
**Time:** 35 minutes

Use PFT (Protection, Fragmentation and Transport) with Reed-Solomon FEC for reliable network transmission.

**You'll learn:**
- Enabling PFT fragmentation
- Configuring Reed-Solomon FEC
- Calculating recovery parameters
- Testing packet loss resilience

[Start Tutorial →](pft-with-fec.md)

---

### [Custom Inputs](custom-inputs.md)

**Difficulty:** Advanced
**Time:** 40 minutes

Create custom input sources by extending python-dabmux's input classes.

**You'll learn:**
- Understanding the InputBase interface
- Creating a custom input class
- Implementing buffer management
- Integrating with the multiplexer

[Start Tutorial →](custom-inputs.md)

---

## Prerequisites

Before starting these tutorials, make sure you have:

1. **python-dabmux installed**: See [Installation Guide](../getting-started/installation.md)
2. **Basic understanding of DAB**: See [Basic Concepts](../getting-started/basic-concepts.md)
3. **Audio files ready**: MPEG Layer II (`.mp2`) or HE-AAC (`.aac`) files

## Tutorial Format

Each tutorial follows this structure:

1. **Overview**: What you'll build and learn
2. **Prerequisites**: What you need before starting
3. **Step-by-step instructions**: Detailed walkthrough
4. **Testing**: How to verify it works
5. **Troubleshooting**: Common issues and solutions
6. **Next steps**: Where to go from here

## Getting Help

If you run into issues:

- Check the [Troubleshooting Guide](../troubleshooting/index.md)
- Read the [FAQ](../faq.md)
- Review the [User Guide](../user-guide/index.md)

## Tutorial Progression

We recommend following tutorials in this order:

```
1. Basic Single Service (start here)
   ↓
2. Multi-Service Ensemble
   ↓
3. DAB+ Setup
   ↓
4. Network Streaming
   ↓
5. PFT with FEC
   ↓
6. Custom Inputs (most advanced)
```

However, you can jump to any tutorial based on your needs.

## Additional Resources

- **[Configuration Reference](../user-guide/configuration/index.md)**: All configuration options
- **[CLI Reference](../user-guide/cli-reference.md)**: Command-line usage
- **[Architecture](../architecture/index.md)**: How python-dabmux works
- **[Examples](../user-guide/configuration/examples.md)**: More configuration examples

---

Ready to start? Begin with [Basic Single Service →](basic-single-service.md)
