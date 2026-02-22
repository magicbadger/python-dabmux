# Documentation Index

Complete guide to all project documentation.

**Last Updated:** 2026-02-22

---

## Quick Navigation

### 🚀 Getting Started
- **[README.md](README.md)** - Project overview and feature list
- **[Quick Start Guide](docs/QUICK_START.md)** - Get running in 5 minutes
- **[Examples](examples/)** - Ready-to-use configuration files

### 📚 User Guides
- **[MOT Carousel Guide](docs/MOT_CAROUSEL_GUIDE.md)** - Complete guide to images, slideshow, and EPG
- **Configuration Reference** - (To be created: complete YAML reference)
- **Remote Control Guide** - (To be created: ZMQ/Telnet API documentation)
- **EDI Output Guide** - (To be created: IP distribution guide)

### 📊 Project Status
- **[Comprehensive Status](COMPREHENSIVE_STATUS.md)** - Complete feature list and statistics
- **[TODO](TODO.md)** - Roadmap, priorities, and future enhancements
- **[CHANGELOG](CHANGELOG.md)** - Version history

---

## Documentation by Category

### Getting Started (3 docs)

**README.md** - Project Overview
- Feature list (22 FIG types)
- Quick start guide
- Command-line usage
- Examples and testing
- 480 lines

**docs/QUICK_START.md** - 5-Minute Setup
- Basic DAB+ setup
- Multi-service configuration
- MOT slideshow setup
- Remote control setup
- Common issues and solutions
- 289 lines

**docs/MOT_CAROUSEL_GUIDE.md** - MOT Complete Guide
- Slideshow mode
- Directory browsing
- EPG (Electronic Programme Guide)
- File formats and optimization
- Troubleshooting
- Dynamic content updates
- 615 lines

---

### Priority Implementation Guides (7 docs)

**Priority 1: Emergency Alerting**
- FIG 0/18 - Announcement Support
- FIG 0/19 - Announcement Switching
- FIG 0/10 - Date and Time
- FIG 0/9 - Extended Country Code
- 38 tests passing

**Priority 2: Service Management & Navigation**
- FIG 0/6 - Service Linking
- FIG 0/21 - Frequency Information
- FIG 0/24 - Other Ensemble Services
- Multi-ensemble networks
- 34 tests passing

**Priority 3: Data Services & Packet Mode**
- FIG 0/3 - Service Component in Packet Mode
- FIG 0/14 - FEC Sub-channel Organization
- MOT Protocol (6 phases)
- 31 tests passing

**Priority 4: Advanced Signalling**
- FIG 0/7 - Configuration Information
- FIG 2/1 - Service Component Dynamic Label
- UTF-8 and emoji support
- 41 tests passing
- See: [PRIORITY4_COMPLETE.md](PRIORITY4_COMPLETE.md)

**Priority 5: EDI Output**
- ETSI TS 102 693 compliant
- UDP/TCP transport
- PFT fragmentation with FEC
- TIST timestamps
- 61 tests passing

**Priority 6: Remote Control & Management**
- Phase 1: ZMQ Foundation (9 tests)
- Phase 2: Parameter Management (15 tests)
- Phase 3: Telnet Interface (23 tests)
- Phase 4: Advanced Features (12 tests)
- 58 tests total
- See: [PRIORITY6_PHASE4_COMPLETE.md](PRIORITY6_PHASE4_COMPLETE.md)

**Priority 7: Conditional Access & Security**
- FIG 6/0 - CA Organization
- FIG 6/1 - CA Service
- 25 tests passing
- See: [PRIORITY7_COMPLETE.md](PRIORITY7_COMPLETE.md)

---

### Configuration Examples (11 files)

Located in `examples/`:

1. **basic_dabplus.yaml** - Simple DAB+ ensemble
2. **multi_service.yaml** - Multi-service configuration
3. **priority1_emergency_alerting.yaml** - EAS demonstration
4. **priority2_service_linking.yaml** - Multi-ensemble networks
5. **priority3_packet_mode.yaml** - Data services and FEC
6. **priority4_advanced_signalling.yaml** - FIG 0/7 & 2/1
7. **priority7_conditional_access.yaml** - CA signaling
8. **mot_carousel_example.yaml** - MOT slideshow
9. **edi_*.yaml** - EDI output examples (4 variants)
10. **zmq_client.py** - Python ZMQ client example

Total: 11 example configurations

---

### Technical Documentation

**COMPREHENSIVE_STATUS.md** - Complete Project Status
- Executive summary
- Feature breakdown by priority (1-7)
- FIG type catalog (22 types)
- Test coverage (1010 tests, 73%)
- Standards compliance
- Deployment readiness
- 436 lines

**TODO.md** - Roadmap and Status
- Currently implemented features
- Test coverage statistics
- Priorities 1-7 (complete)
- Priority 8: Regional Services (future)
- Priority 9: Quality & Compliance (future)
- Future enhancements
- 518 lines

**CHANGELOG.md** - Version History
- Release notes
- Bug fixes
- Feature additions
- Breaking changes
- 162 lines

---

### MOT Protocol Documentation

**MOT_CAROUSEL_GUIDE.md** - Complete MOT Guide
- What is MOT?
- Quick start (3 steps)
- Slideshow mode
  - Image formats (JPEG, PNG)
  - Directory structure
  - Dynamic updates
- Directory browsing mode
  - HTML menus
  - Hierarchical structure
- EPG (Electronic Programme Guide)
  - XML format
  - Schedule updates
- Configuration reference
  - User application types
  - Bitrate recommendations
  - Protection levels
- File format specifications
- Troubleshooting (7 common issues)
- Advanced topics
  - Multiple MOT services
  - Dynamic content updates
  - Best practices
- 615 lines

**Key Sections:**
- Slideshow: Lines 45-180
- Directory Browsing: Lines 182-276
- EPG: Lines 278-347
- Configuration: Lines 349-430
- File Formats: Lines 432-490
- Troubleshooting: Lines 492-580

---

### Priority Completion Documents (7 files)

**PRIORITY4_COMPLETE.md**
- FIG 0/7 implementation details
- FIG 2/1 implementation details
- DynamicLabel dataclass
- 41 tests (17 + 24)
- Configuration examples
- 20,437 bytes

**PRIORITY6_PHASE1_COMPLETE.md**
- ZMQ Foundation
- JSON protocol
- 9 tests
- 12,896 bytes

**PRIORITY6_PHASE2_COMPLETE.md**
- Parameter Management
- 20 commands
- 15 tests
- 14,639 bytes

**PRIORITY6_PHASE3_COMPLETE.md**
- Telnet Interface
- Interactive prompt
- 23 tests
- 18,362 bytes

**PRIORITY6_PHASE4_COMPLETE.md**
- Authentication
- Audit logging
- Runtime logging control
- 12 tests
- 16,366 bytes

**PRIORITY7_COMPLETE.md**
- FIG 6/0 and 6/1 implementation
- ConditionalAccessConfig
- 25 tests
- Security notes
- Production deployment requirements
- Current document

**MOT_PHASE1-6_COMPLETE.md** (6 files)
- Complete MOT implementation
- Carousel engine, slideshow, directory, EPG
- 60+ tests
- Multiple completion documents

---

## Documentation Statistics

### By Type
- **User Guides:** 3 documents (README, Quick Start, MOT Guide)
- **Priority Completion:** 13 documents (all 7 priorities + phases)
- **Configuration Examples:** 11 YAML files
- **Project Status:** 3 documents (Status, TODO, Changelog)

### By Lines of Documentation
- **Total Documentation:** ~3,500+ lines
- **User-Facing Guides:** ~1,400 lines
- **Technical Completion Docs:** ~1,800 lines
- **Configuration Examples:** ~1,200 lines
- **Project Status:** ~1,100 lines

### Coverage
- ✅ **Getting Started** - Complete (README, Quick Start, Examples)
- ✅ **MOT Protocol** - Complete (615-line comprehensive guide)
- ✅ **All Priorities** - Documented (1-7 complete with detailed docs)
- ✅ **Configuration** - Well-documented (11 examples, inline comments)
- ⚠️ **Advanced Topics** - Partial (Remote Control, EDI guides to be created)

---

## Missing Documentation (Future Work)

### To Be Created

**Configuration Reference** - Complete YAML specification
- All fields documented
- Type information
- Default values
- Examples for each field
- Estimated: 200-300 lines

**Remote Control Guide** - ZMQ/Telnet API
- ZMQ protocol specification
- All 20 commands documented
- Python/curl examples
- Authentication guide
- Estimated: 250-350 lines

**EDI Output Guide** - IP distribution
- EDI protocol explanation
- UDP vs TCP modes
- PFT configuration
- TIST timestamps
- Network setup
- Estimated: 200-300 lines

**Emergency Alerting Guide** - EAS implementation
- FIG 0/18 configuration
- FIG 0/19 usage
- Announcement types
- Triggering alerts
- Best practices
- Estimated: 150-200 lines

**Troubleshooting Guide** - Common issues
- Audio problems
- Configuration errors
- Network issues
- Performance tuning
- Debugging steps
- Estimated: 200-250 lines

---

## How to Use This Documentation

### For New Users
1. Start with **[README.md](README.md)** - Overview
2. Follow **[Quick Start Guide](docs/QUICK_START.md)** - Setup
3. Check **[Examples](examples/)** - Copy and modify
4. Review **[MOT Guide](docs/MOT_CAROUSEL_GUIDE.md)** - Add multimedia

### For MOT Carousel
1. Read **[MOT Carousel Guide](docs/MOT_CAROUSEL_GUIDE.md)** - Complete instructions
2. Prepare images (320x240, <50KB)
3. Configure packet mode subchannel
4. Set `carousel_enabled: true`
5. Point to image directory
6. Test and verify

### For Feature Implementation
1. Check **[TODO.md](TODO.md)** - Find priority
2. Read completion document (e.g., PRIORITY4_COMPLETE.md)
3. Review example configuration
4. Check test files for usage examples
5. Review standards section in completion doc

### For Troubleshooting
1. Check **[MOT Carousel Guide](docs/MOT_CAROUSEL_GUIDE.md)** troubleshooting section
2. Review logs with `--verbose` flag
3. Verify configuration with examples
4. Test with etisnoop
5. Check TODO.md for known limitations

---

## Standards Documentation

**ETSI Standards Referenced:**
- **ETSI EN 300 401** - DAB System
- **ETSI EN 300 799** - ETI Specification
- **ETSI TS 102 563** - DAB+ Audio (HE-AAC, Reed-Solomon FEC)
- **ETSI TS 102 693** - EDI Protocol
- **ETSI TS 101 756** - MOT Protocol

**Sections in Completion Docs:**
- Each priority completion document includes standards references
- Byte structures documented per ETSI specs
- Compliance verification results
- Standards-compliant implementations verified with tools

---

## Quick Reference

### Most Important Documents
1. **README.md** - Start here
2. **docs/QUICK_START.md** - Get running quickly
3. **docs/MOT_CAROUSEL_GUIDE.md** - Add multimedia
4. **COMPREHENSIVE_STATUS.md** - Full feature list
5. **TODO.md** - Roadmap and status

### For Specific Features
- **MOT:** docs/MOT_CAROUSEL_GUIDE.md
- **Remote Control:** PRIORITY6_PHASE4_COMPLETE.md
- **Conditional Access:** PRIORITY7_COMPLETE.md
- **Emergency Alerts:** Priority 1 section in TODO.md
- **EDI Output:** Priority 5 section in TODO.md

---

## Contributing to Documentation

**When adding features:**
1. Update COMPREHENSIVE_STATUS.md
2. Update TODO.md (mark as complete)
3. Create PRIORITY*_COMPLETE.md
4. Add example configuration in examples/
5. Update README.md feature list
6. Update this index

**Documentation standards:**
- Use Markdown format
- Include code examples
- Add configuration snippets
- Provide troubleshooting tips
- Reference ETSI standards
- Include test coverage info

---

**Documentation is complete and up-to-date for Priorities 1-7!**

**Status:** 🟢 **Well Documented**

- User guides: Complete
- MOT guide: Complete (615 lines)
- Priority docs: Complete (all 7 priorities)
- Examples: Complete (11 configurations)
- Status: Complete (updated)

**Next:** Create Configuration Reference, Remote Control Guide, and EDI Output Guide (optional enhancements)
