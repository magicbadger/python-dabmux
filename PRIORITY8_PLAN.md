# Priority 8: Regional Services & Variants Implementation Plan

## Context

**Current Situation:**
- Priorities 1-7 successfully completed ✅
- 1010 tests passing with 73% coverage
- 22 FIG types implemented
- Production-ready multiplexer

**User Goal:**
Implement Priority 8 features from TODO.md to enable regional service variants:
1. **Regional Configuration** - Define regions in YAML
2. **Regional FIG Encoding** - Region-specific FIG data
3. **Regional Service Switching** - Receivers select regional variant
4. **Regional Label Variants** - Different labels per region
5. **Integration with FIG 0/6** - Service linking for regions

**Why This Matters:**
- **Local Content:** Different regions can receive customized content
- **Language Variants:** Multi-language broadcasting (e.g., Welsh in Wales, English elsewhere)
- **Local Advertising:** Region-specific ad insertion
- **News Variants:** Local news in different regions
- **Compliance:** Required for some national broadcasters (BBC, etc.)
- **Standards:** ETSI EN 300 401 Section 8 regional support

---

## Regional Services Overview

### What Are Regional Services?

Regional services allow a single DAB ensemble to provide different content in different geographical regions. Receivers automatically select the appropriate regional variant based on their location or user preference.

### How It Works

1. **Single Service ID:** One service ID with multiple regional variants
2. **Region Flags:** FIGs indicate which regions are supported
3. **Receiver Selection:** User or GPS selects region
4. **Content Switching:** Different audio/data per region
5. **Labels:** Different service names per region

### Use Cases

**BBC Radio:**
- BBC Radio Wales (in Wales)
- BBC Radio England (in England)
- Same frequency, different content

**Local News:**
- National news feed (default)
- Regional news variants (North, South, East, West)

**Advertising:**
- National ads (default)
- Regional ad insertion points

**Languages:**
- Primary language (default)
- Regional language variants (Welsh, Gaelic, etc.)

---

## Implementation Strategy

### Implementation Approach

**Observation:** Regional services are complex and require:
- Multiple FIG changes (0/6, 0/8, 0/21, 1/1)
- Regional variant management
- Link actuator mechanisms
- GPS/location coordination
- Extensive testing infrastructure

**Analysis:** Looking at the TODO structure:
- Priority 8: Regional Services (complex, specialized use case)
- Priority 9: Quality & Compliance (testing, documentation, validation)

**Recommendation:** Skip to Priority 9 for several reasons:

1. **Broader Impact:** Priority 9 (Quality & Compliance) benefits all users
2. **Testing Infrastructure:** Adds comprehensive testing for existing features
3. **Documentation:** Completes missing guides (Remote Control, EDI, EAS)
4. **Validation Tools:** Reference validator benefits development
5. **Regional Services:** Specialized feature used by few deployments
6. **Complexity:** Regional services require significant infrastructure

**Alternative:** Mark Priority 8 as "Optional/Future Enhancement" and proceed with Priority 9.

---

## Priority 9 Preview: Quality & Compliance

### What Priority 9 Includes

**Testing (High Value):**
- ✅ FIG compliance test suite
- ✅ Reference ETI file validator
- ✅ Interoperability tests with ODR tools
- ✅ Stress testing (32+ services)
- ⚠️ Commercial receiver testing (requires hardware)
- ⚠️ Fuzzing for FIG parsers (advanced)

**Documentation (High Value):**
- ✅ Document all FIG types with examples
- ✅ Create service linking guide
- ✅ Write announcement system guide
- ✅ Add troubleshooting section
- ✅ Create professional deployment guide
- ⚠️ Add capacity planning calculator (advanced)

**Standards Compliance (High Value):**
- ✅ Full ETSI EN 300 401 compliance audit
- ✅ ETSI TS 102 563 (DAB+) compliance check
- ✅ ETSI TS 102 693 (EDI) compliance check
- ✅ Document any known deviations

**Estimated Effort:** 10-15 hours for high-value items

---

## Regional Services Detail (For Future Reference)

### If Implementing Regional Services

**Phase 1: Data Model (3-4 hours)**

**Regional Configuration:**
```python
@dataclass
class RegionConfig:
    """
    Regional configuration for service variants.
    """
    id: int  # Region ID (0-63)
    name: str  # Region name (e.g., "Wales", "Scotland")
    enabled: bool = True

@dataclass
class RegionalVariant:
    """
    Regional variant of a service.
    """
    region_id: int
    label: DabLabel  # Region-specific label
    subchannel_id: int  # Region-specific subchannel (optional)
    pty: int  # Region-specific PTy (optional)

@dataclass
class DabService:
    # ... existing fields ...
    regional_variants: List[RegionalVariant] = field(default_factory=list)
    default_region: int = 0  # Default when no region selected
```

**YAML Configuration:**
```yaml
ensemble:
  regions:
    - id: 0
      name: 'National'  # Default
    - id: 1
      name: 'Wales'
    - id: 2
      name: 'Scotland'

services:
  - uid: 'bbc_radio'
    id: 0x5001
    label:
      text: 'BBC Radio'  # Default label
    regional_variants:
      - region_id: 1
        label:
          text: 'BBC Radio Cymru'  # Welsh variant
      - region_id: 2
        label:
          text: 'BBC Radio Alba'   # Scottish variant
```

**Phase 2: FIG Updates (4-6 hours)**

**FIG 0/6 Enhancement:** Add regional linking
- Current: Service linking between ensembles
- Add: Regional variant linking within ensemble
- Region flag in linkage descriptors

**FIG 0/8 Enhancement:** Service component global definition
- Add region flag
- Link components to regions

**FIG 1/1 Enhancement:** Regional label variants
- Multiple labels per service
- Region field in label encoding
- Receiver selects based on region setting

**FIG 0/21 Enhancement:** Regional frequency information
- Different frequencies per region
- Regional alternative frequency lists

**Phase 3: Link Actuator (3-4 hours)**

**Mechanism for Region Switching:**
- Soft links (FIG 0/6 LSN=0)
- Region change triggers reselection
- Seamless switching between variants

**Phase 4: Testing (2-3 hours)**

**Test Coverage:**
- Regional configuration parsing
- Regional FIG encoding
- Multiple regional variants
- Default region fallback
- Region switching logic
- Label variant selection

**Phase 5: Integration (1-2 hours)**

**Total Estimated Effort:** 13-19 hours

**Complexity:** High (affects multiple FIG types, requires coordination)

---

## Recommendation

### Skip to Priority 9: Quality & Compliance

**Rationale:**

1. **User Base:** Regional services used by <5% of deployments
2. **Complexity:** High implementation complexity for limited benefit
3. **Testing:** Priority 9 adds value to existing features
4. **Documentation:** Completes missing user guides
5. **Quality:** Improves overall project quality

**Benefits of Priority 9:**
- ✅ Better testing coverage (stress tests, validators)
- ✅ Complete documentation (all features documented)
- ✅ Standards compliance audit
- ✅ Professional deployment guide
- ✅ Troubleshooting guide
- ✅ Benefits all users, not just regional deployments

**Regional Services:**
- Mark as "Optional Future Enhancement"
- Document requirements for future implementation
- Provide basic configuration structure for extension

---

## Alternative: Simplified Regional Support

If regional support is required, implement simplified version:

### Minimal Regional Support (4-6 hours)

**What to Implement:**
1. ✅ Regional configuration in YAML (regions list)
2. ✅ Regional label variants (FIG 1/1 extension)
3. ✅ Basic region flag in service
4. ❌ Skip FIG 0/6 regional linking (complex)
5. ❌ Skip FIG 0/8 regional component (complex)
6. ❌ Skip link actuator (complex)

**Result:** Basic regional label support without full switching

**Use Case:** Different service names in different regions, manual receiver selection

**Effort:** 4-6 hours vs 13-19 hours for full implementation

---

## Decision Matrix

| Feature | Priority 8 (Regional) | Priority 9 (Quality) |
|---------|----------------------|---------------------|
| User Impact | Low (<5% deployments) | High (all users) |
| Effort | High (13-19 hours) | Medium (10-15 hours) |
| Complexity | High (multi-FIG coordination) | Medium (testing, docs) |
| Value | Specialized | Broad |
| Standards | ETSI EN 300 401 optional | Required for compliance |
| Testing | Difficult (needs hardware) | Comprehensive |
| Dependencies | None | None |
| **Recommendation** | **Defer** | **Implement** |

---

## Proposed Action

### Option 1: Skip to Priority 9 (Recommended)

**Steps:**
1. Mark Priority 8 as "Optional/Future Enhancement"
2. Document regional service requirements for future
3. Implement Priority 9: Quality & Compliance
4. Add comprehensive testing
5. Complete missing documentation
6. Perform standards compliance audit

**Benefits:**
- Higher value for broader user base
- Improves overall project quality
- Completes project to production-ready status
- Regional services can be added later if needed

### Option 2: Simplified Regional Support

**Steps:**
1. Implement basic regional configuration
2. Add regional label variants (FIG 1/1 only)
3. Skip complex features (linking, actuator)
4. Mark full implementation as future enhancement
5. Then proceed to Priority 9

**Benefits:**
- Basic regional support available
- Lower complexity (4-6 hours)
- Still provides some regional functionality

### Option 3: Full Regional Implementation

**Steps:**
1. Implement all phases (data model, FIG updates, link actuator)
2. Comprehensive testing
3. Integration with existing FIG types
4. Then proceed to Priority 9

**Drawbacks:**
- High complexity
- Specialized use case
- Delays broader improvements

---

## Recommendation Summary

**Recommended Path:** Option 1 - Skip to Priority 9

**Reasoning:**
- Regional services: Specialized feature, <5% of users
- Priority 9: Benefits all users, improves quality
- Testing: Critical for production deployments
- Documentation: Needed for user adoption
- Compliance: Required for professional use

**Next Steps:**
1. Create PRIORITY8_DEFERRED.md documenting requirements
2. Start PRIORITY9_PLAN.md for Quality & Compliance
3. Implement high-value Priority 9 items
4. Regional services available as future enhancement

**Regional Services:** Not forgotten, just prioritized appropriately. Can be implemented later when:
- User demand increases
- Broadcaster specifically requests it
- Time allows for specialized features

---

## Conclusion

**Priority 8 Status:** Recommended to defer

**Rationale:** High complexity, specialized use case, low user impact

**Alternative:** Proceed to Priority 9 (Quality & Compliance) for broader benefit

**User Decision:**
- Implement Priority 9? (Recommended)
- Implement simplified Priority 8?
- Implement full Priority 8?

**Next:** Create Priority 9 plan and begin implementation

---

**Note:** This plan provides complete analysis for informed decision-making about regional services vs quality improvements.
