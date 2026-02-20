# TODO - Missing DAB/DAB+ Features

This document tracks missing functionality compared to ODR-DabMux and the ETSI DAB specifications.

## Status Summary

**Currently Implemented FIG Types:**
- ✅ FIG 0/0: Ensemble information
- ✅ FIG 0/1: Subchannel organization
- ✅ FIG 0/2: Service component description
- ✅ FIG 0/5: Service component language
- ✅ FIG 0/8: Service component global definition
- ✅ FIG 0/13: User application information
- ✅ FIG 0/17: Programme Type
- ✅ FIG 1/0: Ensemble label
- ✅ FIG 1/1: Service labels
- ✅ FIG 1/4: Service component labels

---

## Priority 1: Emergency Alerting & Notifications

Essential for Emergency Alert System (EAS) functionality.

### FIG 0/18 - Announcement Support
- [ ] Implement FIG 0/18 encoding
- [ ] Add announcement cluster configuration to YAML
- [ ] Support announcement types:
  - [ ] Alarm (emergency)
  - [ ] Traffic
  - [ ] Weather
  - [ ] News flash
  - [ ] Area weather flash
  - [ ] Event announcement
  - [ ] Special event
  - [ ] Programme information
  - [ ] Sport report
  - [ ] Financial report
- [ ] Add per-service announcement flags
- [ ] Write unit tests for FIG 0/18

**Specification:** ETSI EN 300 401 Section 8.1.6.3

### FIG 0/19 - Announcement Switching
- [ ] Implement FIG 0/19 encoding
- [ ] Add announcement state management
- [ ] Support announcement switching triggers
- [ ] Add cluster ID to subchannel mapping
- [ ] Support new/repeated flag
- [ ] Add region ID support (optional)
- [ ] Write unit tests for FIG 0/19
- [ ] Create example configuration with announcements

**Specification:** ETSI EN 300 401 Section 8.1.6.4

### FIG 0/10 - Date and Time
- [ ] Implement FIG 0/10 encoding
- [ ] Add system time source configuration
- [ ] Calculate Modified Julian Date (MJD)
- [ ] Add UTC/LSI (Leap Second Indicator) support
- [ ] Support LTO (Local Time Offset) - requires FIG 0/9
- [ ] Add millisecond precision (optional)
- [ ] Write unit tests for FIG 0/10
- [ ] Handle leap seconds correctly

**Specification:** ETSI EN 300 401 Section 8.1.3.3

### FIG 0/9 - Extended Country Code & LTO
- [ ] Implement FIG 0/9 encoding (long form)
- [ ] Add ECC (Extended Country Code) configuration
- [ ] Add LTO (Local Time Offset) configuration
- [ ] Support international table ID
- [ ] Write unit tests for FIG 0/9

**Specification:** ETSI EN 300 401 Section 8.1.3.2

---

## Priority 2: Service Management & Navigation

Enables multi-ensemble networks and service discovery.

### FIG 0/6 - Service Linking
- [ ] Implement FIG 0/6 encoding
- [ ] Support IdLQ (ID List Qualifier) modes:
  - [ ] Mode 0: DAB services in other ensembles
  - [ ] Mode 1: RDS/FM services
  - [ ] Mode 2: DRM services
  - [ ] Mode 3: AMSS services
- [ ] Support LSN (Linkage Set Number)
- [ ] Add hard/soft linking flag
- [ ] Add ILS (International Linkage Set) support
- [ ] Create service linking configuration schema
- [ ] Write unit tests for FIG 0/6
- [ ] Document service linking examples

**Specification:** ETSI EN 300 401 Section 8.1.15

### FIG 0/24 - Other Ensemble (OE) Services
- [ ] Implement FIG 0/24 encoding
- [ ] Add OE service list configuration
- [ ] Support CAId (Conditional Access ID)
- [ ] Support ECC and ensemble reference
- [ ] Auto-generate from service linking config
- [ ] Write unit tests for FIG 0/24
- [ ] Test with multi-ensemble scenarios

**Specification:** ETSI EN 300 401 Section 8.1.10.3

### FIG 0/21 - Frequency Information (FI)
- [ ] Implement FIG 0/21 encoding
- [ ] Support FI list configuration
- [ ] Add frequency range definitions
- [ ] Support continuity flag
- [ ] Add length indicator
- [ ] Support ID field for multiple lists
- [ ] Write unit tests for FIG 0/21
- [ ] Create frequency list examples

**Specification:** ETSI EN 300 401 Section 8.1.8

---

## Priority 3: Data Services & Packet Mode

Required for non-audio data services.

### FIG 0/3 - Service Component in Packet Mode
- [ ] Implement FIG 0/3 encoding
- [ ] Add packet mode subchannel support
- [ ] Support CAOrg (Conditional Access Organization)
- [ ] Add packet address configuration
- [ ] Support DG flag (Data Groups)
- [ ] Write unit tests for FIG 0/3
- [ ] Create packet mode examples

**Specification:** ETSI EN 300 401 Section 6.3.1

### FIG 0/14 - FEC Sub-channel Organization
- [ ] Implement FIG 0/14 encoding
- [ ] Add FEC scheme configuration
- [ ] Support sub-channel organization for packet mode
- [ ] Write unit tests for FIG 0/14

**Specification:** ETSI EN 300 401 Section 6.2.1

---

## Priority 4: Advanced Signalling

### FIG 0/7 - Configuration Information
- [ ] Implement FIG 0/7 encoding
- [ ] Add reconfiguration counter management
- [ ] Support Count field
- [ ] Write unit tests for FIG 0/7

**Specification:** ETSI EN 300 401 Section 8.1.16

### FIG 2 - Labels with Character Sets
- [ ] Implement FIG 2/0 (Ensemble label - UTF-8)
- [ ] Implement FIG 2/1 (Service label - UTF-8)
- [ ] Implement FIG 2/4 (Component label - UTF-8)
- [ ] Implement FIG 2/5 (Data service label - UTF-8)
- [ ] Add character set configuration
- [ ] Support text control field
- [ ] Add toggle/segment flags
- [ ] Write unit tests for FIG 2/x
- [ ] Test with non-ASCII labels

**Specification:** ETSI EN 300 401 Section 8.1.13

---

## Priority 5: Output Formats

### EDI (Ensemble Data Interface)
- [ ] Research EDI packet format (ETSI TS 102 693)
- [ ] Implement EDI-AF (EDI with AF packets)
- [ ] Implement EDI-PF (EDI with PF packets)
- [ ] Support EDI over UDP
- [ ] Support EDI over TCP
- [ ] Add timestamp synchronization (PTP/NTP)
- [ ] Implement error protection (Reed-Solomon)
- [ ] Add sequence numbers
- [ ] Write unit tests for EDI encoding
- [ ] Create EDI output examples

**Specification:** ETSI TS 102 693

### Enhanced ETI Output
- [ ] Add timestamp metadata to ETI frames
- [ ] Support ETI-NI (Network Independent) format validation
- [ ] Add TIST (Time Stamp) field support

---

## Priority 6: Remote Control & Management

### ZeroMQ Remote Control
- [ ] Add ZeroMQ dependency
- [ ] Implement ZMQ request/reply pattern
- [ ] Support runtime parameter changes:
  - [ ] Service labels
  - [ ] Programme type
  - [ ] Announcement flags
  - [ ] Input source switching
- [ ] Add statistics reporting
- [ ] Implement authentication (optional)
- [ ] Write ZMQ client examples
- [ ] Document ZMQ protocol

### Management Interface
- [ ] Implement Telnet management server
- [ ] Add command parser
- [ ] Support live parameter queries
- [ ] Add input source status monitoring
- [ ] Implement configuration reload
- [ ] Add logging level control
- [ ] Create management CLI documentation

---

## Priority 7: Conditional Access & Security

### FIG 6 - Conditional Access
- [ ] Research CA requirements
- [ ] Implement FIG 6/0 (CA organization)
- [ ] Implement FIG 6/1 (CA service)
- [ ] Support CA system identification
- [ ] Add CA configuration schema
- [ ] Write unit tests for FIG 6/x

**Specification:** ETSI EN 300 401 Section 11

---

## Priority 8: Regional Services & Variants

### Regional Variant Support
- [ ] Add region configuration to YAML
- [ ] Implement region-specific FIG encoding
- [ ] Support regional service switching
- [ ] Integrate with FIG 0/6 (service linking)
- [ ] Add regional label variants
- [ ] Create regional configuration examples

---

## Priority 9: Quality & Compliance

### Testing
- [ ] Add FIG compliance test suite
- [ ] Create reference ETI file validator
- [ ] Add interoperability tests with ODR tools
- [ ] Test with commercial DAB receivers
- [ ] Add stress testing (32+ services)
- [ ] Implement fuzzing for FIG parsers

### Documentation
- [ ] Document all FIG types with examples
- [ ] Create service linking guide
- [ ] Write announcement system guide
- [ ] Add troubleshooting section
- [ ] Create professional deployment guide
- [ ] Add capacity planning calculator

### Standards Compliance
- [ ] Full ETSI EN 300 401 compliance audit
- [ ] ETSI TS 102 563 (DAB+) compliance check
- [ ] ETSI TS 102 693 (EDI) compliance check
- [ ] Document any known deviations

---

## Future Enhancements

### Input Sources
- [ ] Add ZeroMQ audio input
- [ ] Support Icecast/SHOUTcast input
- [ ] Add JACK audio input
- [ ] Support ALSA input (live audio)
- [ ] Add input failover/redundancy

### Advanced Features
- [ ] Service following (seamless handover)
- [ ] Dynamic label plus (DL+)
- [ ] MOT Slideshow
- [ ] Journaline text service
- [ ] EPG (Electronic Programme Guide)
- [ ] TMC (Traffic Message Channel)

### Performance
- [ ] Multi-threaded encoding
- [ ] SIMD optimizations for FEC
- [ ] Memory pool for buffer management
- [ ] Zero-copy packet processing

---

## References

- **ETSI EN 300 401**: DAB System Specification
- **ETSI TS 102 563**: DAB+ Audio Specification
- **ETSI TS 102 693**: EDI Specification
- **ODR-DabMux**: https://github.com/Opendigitalradio/ODR-DabMux
- **ODR Documentation**: https://opendigitalradio.github.io/mmbtools-doc/

---

## Notes

**Current Capability:**
- ✅ Excellent for basic multi-service DAB+ multiplexing
- ✅ Tested with up to 32 simultaneous services @ 89% capacity
- ✅ 100% decode success rate with ODR-encoded audio
- ✅ Full ETI output support

**Limitations for Production Use:**
- ❌ No emergency alerting capability (missing FIG 0/18/19)
- ❌ No service networks (missing FIG 0/6/21/24)
- ❌ No EDI output for modern broadcast chains
- ❌ No runtime control (missing ZMQ/management)
- ❌ Limited to audio services (no packet mode)

**Minimum Viable for Emergency Alerts:**
1. FIG 0/18 (announcement support)
2. FIG 0/19 (announcement switching)
3. FIG 0/10 (date/time)

**Minimum Viable for Professional Deployment:**
1. Items above, plus:
2. FIG 0/6 (service linking)
3. FIG 0/21 (frequency info)
4. EDI output
5. ZeroMQ remote control
