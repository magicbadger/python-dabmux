# TODO - Missing DAB/DAB+ Features

This document tracks missing functionality compared to ODR-DabMux and the ETSI DAB specifications.

## Status Summary

**Currently Implemented FIG Types:**
- ✅ FIG 0/0: Ensemble information
- ✅ FIG 0/1: Subchannel organization
- ✅ FIG 0/2: Service component description
- ✅ FIG 0/3: Service component in packet mode (Priority 3) ⭐ NEW
- ✅ FIG 0/5: Service component language
- ✅ FIG 0/6: Service linking (Priority 2)
- ✅ FIG 0/8: Service component global definition
- ✅ FIG 0/9: Extended Country Code & LTO (Priority 1)
- ✅ FIG 0/10: Date and Time (Priority 1)
- ✅ FIG 0/13: User application information
- ✅ FIG 0/14: FEC sub-channel organization (Priority 3) ⭐ NEW
- ✅ FIG 0/17: Programme Type
- ✅ FIG 0/18: Announcement Support (Priority 1)
- ✅ FIG 0/19: Announcement Switching (Priority 1)
- ✅ FIG 0/21: Frequency Information (Priority 2)
- ✅ FIG 0/24: Other Ensemble Services (Priority 2)
- ✅ FIG 1/0: Ensemble label
- ✅ FIG 1/1: Service labels
- ✅ FIG 1/4: Service component labels

**Test Coverage:**
- 763 passing tests (72 for Priority 1-3, 61 for Priority 5 EDI)
- Comprehensive unit tests for all FIG types
- Integration tested with dablin and etisnoop
- EDI output tested with TCP/UDP transport and CLI integration

---

## Priority 1: Emergency Alerting & Notifications ✅ COMPLETED

Essential for Emergency Alert System (EAS) functionality.

### FIG 0/18 - Announcement Support ✅
- ✅ Implement FIG 0/18 encoding
- ✅ Add announcement cluster configuration to YAML
- ✅ Support announcement types:
  - ✅ Alarm (emergency)
  - ✅ Traffic
  - ✅ Weather
  - ✅ News flash
  - ✅ Transport flash
  - ✅ Warning/service
  - ✅ Event announcement
  - ✅ Special event
  - ✅ Programme information
  - ✅ Sport report
  - ✅ Financial report
- ✅ Add per-service announcement flags
- ✅ Write unit tests for FIG 0/18 (20 tests)
- ✅ Support new_flag and region_flag

**Specification:** ETSI EN 300 401 Section 8.1.6.3

### FIG 0/19 - Announcement Switching ✅
- ✅ Implement FIG 0/19 encoding
- ✅ Add announcement state management (active_announcements list)
- ✅ Support announcement switching triggers
- ✅ Add cluster ID to subchannel mapping
- ✅ Support new/repeated flag
- ✅ Add region ID support (optional)
- ✅ Dynamic priority/rate (HIGH when active)
- ✅ Write unit tests for FIG 0/19 (18 tests)
- ✅ Create example configuration with announcements

**Specification:** ETSI EN 300 401 Section 8.1.6.4

### FIG 0/10 - Date and Time ✅
- ✅ Implement FIG 0/10 encoding
- ✅ Add system time source configuration
- ✅ Calculate Modified Julian Date (MJD)
- ✅ Add UTC flag support
- ✅ Support LTO (Local Time Offset) with FIG 0/9
- ✅ Auto-calculate LTO from system timezone
- ✅ Manual and system time sources
- ✅ Confidence indicator support
- ✅ Write unit tests for FIG 0/10 (10 tests)

**Specification:** ETSI EN 300 401 Section 8.1.3.3

### FIG 0/9 - Extended Country Code & LTO ✅
- ✅ Implement FIG 0/9 encoding (long form)
- ✅ Add ECC (Extended Country Code) configuration
- ✅ Add LTO (Local Time Offset) configuration
- ✅ Support international table ID
- ✅ Auto-calculate LTO from system timezone
- ✅ Write unit tests for FIG 0/9 (10 tests)

**Specification:** ETSI EN 300 401 Section 8.1.3.2

---

## Priority 2: Service Management & Navigation ✅ COMPLETED

Enables multi-ensemble networks and service discovery.

### FIG 0/6 - Service Linking ✅
- ✅ Implement FIG 0/6 encoding
- ✅ Support IdLQ (ID List Qualifier) modes:
  - ✅ Mode 0: DAB services in other ensembles
  - ✅ Mode 1: RDS/FM services
  - ✅ Mode 2: DRM services
  - ✅ Mode 3: AMSS services
- ✅ Support LSN (Linkage Set Number) - 12-bit field
- ✅ Add hard/soft linking flag
- ✅ Add ILS (International Linkage Set) support
- ✅ Create service linking configuration schema
- ✅ Support 16-bit and 32-bit service IDs
- ✅ RDS PI code and FM frequency encoding
- ✅ Iterative transmission for multiple links
- ✅ Write unit tests for FIG 0/6 (16 tests)
- ✅ Document service linking examples

**Specification:** ETSI EN 300 401 Section 8.1.15

### FIG 0/24 - Other Ensemble (OE) Services ✅
- ✅ Implement FIG 0/24 encoding
- ✅ Add OE service list configuration
- ✅ Support CAId (Conditional Access ID)
- ✅ Support ECC and ensemble reference
- ✅ Group services by ensemble
- ✅ Support 16-bit and 32-bit service IDs
- ✅ Iterative transmission for multiple ensembles
- ✅ Write unit tests for FIG 0/24 (11 tests)
- ✅ Test with multi-ensemble scenarios

**Specification:** ETSI EN 300 401 Section 8.1.10.3

### FIG 0/21 - Frequency Information (FI) ✅
- ✅ Implement FIG 0/21 encoding
- ✅ Support multiple frequency lists per service
- ✅ DAB frequency encoding (MHz × 16)
- ✅ FM frequency encoding ((MHz - 87.5) × 200)
- ✅ Support continuity flag (0-3)
- ✅ Support R flag (list complete)
- ✅ Support list ID field (0-15)
- ✅ Mixed DAB/FM frequency lists
- ✅ Iterative transmission
- ✅ Write unit tests for FIG 0/21 (14 tests)
- ✅ Create comprehensive frequency list examples

**Specification:** ETSI EN 300 401 Section 8.1.8

---

## Priority 3: Data Services & Packet Mode ✅ COMPLETED

Enables non-audio data services with packet addressing and FEC protection.

### FIG 0/3 - Service Component in Packet Mode ✅
- ✅ Implement FIG 0/3 encoding
- ✅ Add packet mode subchannel support
- ✅ Support CAOrg (Conditional Access Organization)
- ✅ Add packet address configuration (10-bit, 0-1023)
- ✅ Support DG flag (Data Groups)
- ✅ Support DSCTy (Data Service Component Type)
- ✅ TMid=01 (packet mode) vs TMid=00 (stream mode)
- ✅ 3 bytes per component (vs 2 bytes for stream)
- ✅ Programme/data service alternation
- ✅ Iterative transmission support
- ✅ Write unit tests for FIG 0/3 (18 tests)
- ✅ Create packet mode examples (MOT, EPG, Journaline)

**Specification:** ETSI EN 300 401 Section 8.1.4

### FIG 0/14 - FEC Sub-channel Organization ✅
- ✅ Implement FIG 0/14 encoding
- ✅ Add FEC scheme configuration (0-3)
- ✅ Support RS(204, 188) Reed-Solomon FEC (scheme 1)
- ✅ Conditional registration (only when FEC enabled)
- ✅ Iterative transmission for multiple FEC subchannels
- ✅ Write unit tests for FIG 0/14 (13 tests)
- ✅ Integrate with packet mode subchannels

**Specification:** ETSI EN 300 401 Section 8.1.5

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

## Priority 5: Output Formats ✅ COMPLETED

### EDI (Ensemble Data Interface)
- ✅ Research EDI packet format (ETSI TS 102 693)
- ✅ Implement TAG items (*ptr, deti, est, tist)
- ✅ Implement EDI-AF (EDI with AF packets)
- ✅ Support EDI over UDP (multicast & unicast)
- ✅ Support EDI over TCP (client & server modes)
- ✅ Add timestamp synchronization (TIST TAG with Unix conversion)
- ✅ Implement PFT fragmentation (Protocol with Forward error correction & Timestamp)
- ✅ Add sequence numbers (AF packet sequencing)
- ✅ Write unit tests for EDI encoding (61 tests total):
  - ✅ 20 tests for TIST timestamps
  - ✅ 15 tests for TCP transport
  - ✅ 14 tests for multiplexer integration
  - ✅ 16 tests for CLI configuration
  - ✅ 10 tests for end-to-end integration
- ✅ Integrate with multiplexer (automatic EDI transmission)
- ✅ Add CLI arguments (--edi, --edi-destination, --edi-protocol, --pft, --tist)
- ✅ Create EDI output YAML configuration schema
- ✅ Create EDI output examples (udp_multicast, tcp_client, tcp_server, pft_fec)
- ✅ Add validation tools (edi_analyzer, edi_generator)
- ✅ Add end-to-end integration tests (UDP, TCP, PFT, multicast, combined)

**Specification:** ETSI TS 102 693

**Implementation Status:**
- Phase 1 (TIST & Timestamps): ✅ Complete
- Phase 2 (TCP Transport): ✅ Complete
- Phase 3 (Multiplexer Integration): ✅ Complete
- Phase 4 (CLI & Configuration): ✅ Complete
- Phase 5 (Testing & Validation): ✅ Complete

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
- ✅ **Emergency alerting system ready** (FIG 0/9, 0/10, 0/18, 0/19)
- ✅ **Multi-ensemble networks** (FIG 0/6, 0/21, 0/24)
- ✅ **Service linking and frequency management**
- ✅ **Date/time synchronization with LTO**
- ✅ **Data services with packet mode** (FIG 0/3, 0/14)
- ✅ **FEC protection for packet data** (RS 204,188)
- ✅ **Packet addressing for component multiplexing**
- ✅ **MOT, EPG, Journaline support**
- ✅ **EDI output with TCP/UDP transport** (Priority 5 complete) ⭐ NEW
- ✅ **TIST timestamp synchronization** ⭐ NEW
- ✅ **PFT fragmentation for error protection** ⭐ NEW
- ✅ **CLI integration for EDI streaming** ⭐ NEW
- ✅ **763 passing tests** with comprehensive coverage

**Remaining Limitations for Production Use:**
- ⚠️ No runtime control (missing ZMQ/management) (Priority 6)
- ⚠️ No advanced signalling (FIG 0/7, FIG 2/x) (Priority 4)

**✅ Core FIG Signaling: COMPLETE**
All fundamental DAB multiplex configuration information (MCI) implemented:
1. ✅ FIG 0/18, 0/19 (announcement support & switching)
2. ✅ FIG 0/10 (date/time)
3. ✅ FIG 0/9 (ECC/LTO)
4. ✅ FIG 0/6, 0/21, 0/24 (service linking & navigation)
5. ✅ FIG 0/3, 0/14 (packet mode data services & FEC) ⭐ NEW

**Professional Deployment Readiness:**
- ✅ Emergency alerting: **READY** (Priority 1 complete)
- ✅ Multi-ensemble networks: **READY** (Priority 2 complete)
- ✅ Data services (packet mode): **READY** (Priority 3 complete)
- ✅ Modern broadcast chains: **READY** (Priority 5 complete) ⭐ NEW
  - ✅ EDI protocol implementation complete
  - ✅ TCP/UDP transport working
  - ✅ CLI configuration complete
  - ✅ PFT/FEC for error protection
  - ✅ 61 tests with validation tools
- ⚠️ Remote management: Needs ZMQ control (Priority 6)
