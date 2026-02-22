# Priority 7: Conditional Access & Security Implementation Plan

## Context

**Current Situation:**
- Priorities 1-6 successfully completed ✅
- 985 tests passing with 73% coverage
- All core DAB signaling implemented
- Production-ready multiplexer

**User Goal:**
Implement Priority 7 features from TODO.md to enable Conditional Access (CA) for DAB services:
1. **FIG 6/0** - CA Organization
2. **FIG 6/1** - CA Service

**Why This Matters:**
- **Commercial Broadcasting:** Enables subscription-based services
- **Content Protection:** Prevents unauthorized reception
- **Revenue Generation:** Pay-radio services
- **Compliance:** Required for commercial DAB deployments
- **Standards:** ETSI EN 300 401 Section 11 compliance

---

## Conditional Access Overview

### What is Conditional Access?

Conditional Access (CA) allows broadcasters to control who can access DAB services by encrypting the audio/data content. Only receivers with valid decryption keys (usually via subscription cards) can decode the content.

### CA System Components

1. **CA System Identifier (CAId):** Unique ID for the CA provider (16-bit)
2. **CA Organization (CAOrg):** Organization providing CA services
3. **CA Mode:** How CA is applied (stream/packet mode)
4. **ECM/EMM:** Entitlement Control/Management Messages (not handled by mux)

### FIG 6 Types

#### FIG 6/0: CA Organization
**Purpose:** Declares which CA systems are used in the ensemble

**Byte Structure:**
```
Header (2 bytes) + CA Org entries (variable)

FIG Header:
┌────────────────┬──────────────────────────┐
│ Type (3) = 6   │ CN | OE | PD | Ext (5)  │
│ Length (5)     │  0 |  0 |  0 |    0     │
└────────────────┴──────────────────────────┘

Per CA Organization (2 bytes):
┌──────────────────────────────────┐
│ CAId (16 bits)                   │ CA System ID
└──────────────────────────────────┘
```

**Key Fields:**
- **CAId** (16 bits): CA system identifier (e.g., 0x5601 for Nagravision)
- Multiple CA systems can be signaled

**When to Transmit:**
- Rate C (once per second if CA is used)
- Only when ensemble uses CA

#### FIG 6/1: CA Service
**Purpose:** Indicates which services use Conditional Access

**Byte Structure:**
```
Header (2 bytes) + Service entries (variable)

FIG Header:
┌────────────────┬──────────────────────────┐
│ Type (3) = 6   │ CN | OE | PD | Ext (5)  │
│ Length (5)     │  0 |  0 |  1 |    1     │
└────────────────┴──────────────────────────┘

Per Service Entry:
┌────────────────────────────────────────────┐
│ SId (16 or 32 bits)                        │ Service ID
├────────────────────────────────────────────┤
│ CAId (16 bits)                             │ CA System ID
└────────────────────────────────────────────┘
```

**Key Fields:**
- **SId** (16/32 bits): Service ID (16-bit for programme, 32-bit for data)
- **CAId** (16 bits): CA system identifier for this service
- **L/S flag** (in PD bit): 0=16-bit SId, 1=32-bit SId

**When to Transmit:**
- Rate C (once per second)
- Only for services using CA

---

## CA System Identifiers (CAId)

Common CA systems in DAB:
- `0x0000` - No CA (free-to-air)
- `0x5501` - Viaccess
- `0x5601` - Nagravision (Kudelski)
- `0x5901` - VideoGuard
- `0x4A10` - DigitalRadio CA
- `0xFFFF` - Proprietary/Test systems

**Note:** CAId assignment is managed by the DVB Project.

---

## Implementation Strategy

### Phase 1: Data Model & Configuration (1-2 hours)

**Add CA configuration to mux_elements.py:**
```python
@dataclass
class ConditionalAccessConfig:
    """
    Conditional Access configuration.

    Defines CA systems and which services use them.
    """
    enabled: bool = False
    systems: List[int] = field(default_factory=list)  # List of CAId values

@dataclass
class DabService:
    # ... existing fields ...
    ca_system: Optional[int] = None  # CAId if service uses CA, None for FTA
```

**Configuration Schema:**
```yaml
ensemble:
  conditional_access:
    enabled: true
    systems:
      - 0x5601  # Nagravision
      - 0x4A10  # DigitalRadio CA

services:
  - uid: 'premium_service'
    id: 0x5001
    ca_system: 0x5601  # This service uses Nagravision

  - uid: 'free_service'
    id: 0x5002
    ca_system: null  # Free-to-air (no CA)
```

### Phase 2: FIG 6/0 Implementation (2-3 hours)

**File:** `src/dabmux/fig/fig6.py` (NEW)

```python
"""
FIG Type 6 implementations.

FIG Type 6 contains Conditional Access information.
"""
import struct
import structlog
from typing import List
from dabmux.fig.base import FIGBase, FIGRate, FillStatus, FIGPriority
from dabmux.core.mux_elements import DabEnsemble

logger = structlog.get_logger()


class FIG6_0(FIGBase):
    """
    FIG 6/0: Conditional Access Organization.

    Declares which CA systems are used in the ensemble.
    Per ETSI EN 300 401 Section 11.2.1.
    """

    def __init__(self, ensemble: DabEnsemble) -> None:
        super().__init__()
        self.ensemble = ensemble

    def fill(self, buf: bytearray, max_size: int) -> FillStatus:
        """Fill buffer with FIG 6/0 data."""
        status = FillStatus()

        # Check if CA is enabled
        if not self.ensemble.conditional_access or not self.ensemble.conditional_access.enabled:
            status.complete_fig_transmitted = True
            return status

        systems = self.ensemble.conditional_access.systems
        if not systems:
            status.complete_fig_transmitted = True
            return status

        # Calculate required size: 2 (header) + 2 * num_systems
        required = 2 + (len(systems) * 2)
        if max_size < required:
            return status

        # Encode header
        fig_type = 6
        length = (len(systems) * 2) + 1  # Data bytes + byte 1
        cn = 0
        oe = 0
        pd = 0
        extension = 0

        buf[0] = (fig_type << 5) | (length & 0x1F)
        buf[1] = (cn << 7) | (oe << 6) | (pd << 5) | (extension & 0x1F)

        # Encode CA system IDs
        pos = 2
        for caid in systems:
            struct.pack_into('>H', buf, pos, caid & 0xFFFF)
            pos += 2

        status.num_bytes_written = pos
        status.complete_fig_transmitted = True

        return status

    def repetition_rate(self) -> FIGRate:
        """FIG 6/0 transmitted at rate C (once per second)."""
        return FIGRate.C

    def priority(self) -> FIGPriority:
        """FIG 6/0 is NORMAL priority."""
        return FIGPriority.NORMAL

    def fig_type(self) -> int:
        """FIG type 6."""
        return 6

    def fig_extension(self) -> int:
        """Extension 0."""
        return 0
```

### Phase 3: FIG 6/1 Implementation (2-3 hours)

**Add to `src/dabmux/fig/fig6.py`:**

```python
class FIG6_1(FIGBase):
    """
    FIG 6/1: Conditional Access Service.

    Indicates which services use Conditional Access.
    Per ETSI EN 300 401 Section 11.2.2.
    """

    def __init__(self, ensemble: DabEnsemble) -> None:
        super().__init__()
        self.ensemble = ensemble
        self.service_index = 0

    def fill(self, buf: bytearray, max_size: int) -> FillStatus:
        """Fill buffer with FIG 6/1 data."""
        status = FillStatus()

        # Get services with CA
        ca_services = [s for s in self.ensemble.services if s.ca_system is not None]

        if not ca_services:
            status.complete_fig_transmitted = True
            return status

        if max_size < 4:  # Minimum: header(2) + entry(2 or 4)
            return status

        # Reserve space for header
        pos = 2
        services_written = 0

        # Write service entries
        while self.service_index < len(ca_services) and pos < max_size:
            service = ca_services[self.service_index]

            # Determine SId size
            is_data = service.id >= 0x10000  # Data services use 32-bit SId
            sid_size = 4 if is_data else 2
            entry_size = sid_size + 2  # SId + CAId

            if pos + entry_size > max_size:
                break  # Not enough space

            # Encode SId
            if is_data:
                struct.pack_into('>I', buf, pos, service.id)
                pos += 4
            else:
                struct.pack_into('>H', buf, pos, service.id)
                pos += 2

            # Encode CAId
            struct.pack_into('>H', buf, pos, service.ca_system & 0xFFFF)
            pos += 2

            services_written += 1
            self.service_index += 1

        if services_written == 0:
            return status

        # Fill header
        fig_type = 6
        length = (pos - 2) + 1  # Data bytes + byte 1
        cn = 0
        oe = 0
        pd = 1 if any(s.id >= 0x10000 for s in ca_services[:self.service_index]) else 0
        extension = 1

        buf[0] = (fig_type << 5) | (length & 0x1F)
        buf[1] = (cn << 7) | (oe << 6) | (pd << 5) | (extension & 0x1F)

        status.num_bytes_written = pos

        # Check if complete
        if self.service_index >= len(ca_services):
            status.complete_fig_transmitted = True
            self.service_index = 0

        return status

    def repetition_rate(self) -> FIGRate:
        """FIG 6/1 transmitted at rate C (once per second)."""
        return FIGRate.C

    def priority(self) -> FIGPriority:
        """FIG 6/1 is NORMAL priority."""
        return FIGPriority.NORMAL

    def fig_type(self) -> int:
        """FIG type 6."""
        return 6

    def fig_extension(self) -> int:
        """Extension 1."""
        return 1
```

### Phase 4: Integration (1 hour)

**File:** `src/dabmux/fig/fic.py`

Import and register FIG 6 types:
```python
from dabmux.fig.fig6 import FIG6_0, FIG6_1

# In _setup_figs():
# FIG 6/0: CA Organization (if CA enabled)
if self.ensemble.conditional_access and self.ensemble.conditional_access.enabled:
    fig6_0 = FIG6_0(self.ensemble)
    self.carousel.add_fig(fig6_0)

    # FIG 6/1: CA Service (if any services use CA)
    if any(s.ca_system is not None for s in self.ensemble.services):
        fig6_1 = FIG6_1(self.ensemble)
        self.carousel.add_fig(fig6_1)
```

**File:** `src/dabmux/fig/__init__.py`

Export FIG 6 types:
```python
from dabmux.fig.fig6 import FIG6_0, FIG6_1
```

### Phase 5: Testing (3-4 hours)

**File:** `tests/unit/test_fig6.py` (NEW)

Tests needed (~20 tests):

**FIG 6/0 Tests (10 tests):**
1. Header encoding (Type 6, Extension 0)
2. Single CA system encoding
3. Multiple CA systems encoding
4. CAId field encoding (16-bit)
5. No CA systems (empty list)
6. CA disabled (skip transmission)
7. Maximum CA systems (space limit)
8. Repetition rate (FIGRate.C)
9. Priority (NORMAL)
10. FIG type and extension

**FIG 6/1 Tests (10 tests):**
1. Header encoding (Type 6, Extension 1, PD flag)
2. Single service with CA encoding
3. Multiple services with CA encoding
4. 16-bit SId encoding (programme services)
5. 32-bit SId encoding (data services)
6. Mixed SId sizes (PD flag handling)
7. No CA services (skip transmission)
8. Iterative transmission (multiple calls)
9. Space limitation handling
10. Repetition rate and priority

---

## Configuration Examples

### Example 1: Premium Subscription Service

```yaml
ensemble:
  id: 0xCE15
  ecc: 0xE1
  label:
    text: 'Premium DAB'
    short_text: 'Premium'

  conditional_access:
    enabled: true
    systems:
      - 0x5601  # Nagravision

services:
  # Premium service with CA
  - uid: 'premium_music'
    id: 0x5001
    label:
      text: 'Premium Music'
      short_text: 'Premium'
    ca_system: 0x5601  # Requires Nagravision subscription

  # Free-to-air service
  - uid: 'free_news'
    id: 0x5002
    label:
      text: 'Free News'
      short_text: 'News'
    ca_system: null  # Free-to-air
```

### Example 2: Multi-CA System

```yaml
ensemble:
  conditional_access:
    enabled: true
    systems:
      - 0x5601  # Nagravision
      - 0x4A10  # DigitalRadio CA

services:
  - uid: 'service_a'
    id: 0x5001
    ca_system: 0x5601  # Nagravision

  - uid: 'service_b'
    id: 0x5002
    ca_system: 0x4A10  # DigitalRadio CA

  - uid: 'service_c'
    id: 0x5003
    ca_system: null  # Free-to-air
```

---

## Critical Files Summary

### Files to Create (2 files):
1. `src/dabmux/fig/fig6.py` - FIG 6/0 and 6/1 implementations (~200 LOC)
2. `tests/unit/test_fig6.py` - FIG 6 tests (20 tests, ~400 LOC)

### Files to Modify (4 files):
1. `src/dabmux/core/mux_elements.py` (+20 LOC)
   - Add `ConditionalAccessConfig` dataclass
   - Add `ca_system` field to `DabService`
   - Add `conditional_access` field to `DabEnsemble`

2. `src/dabmux/fig/fic.py` (+10 LOC)
   - Import FIG6_0 and FIG6_1
   - Register FIG 6 types conditionally

3. `src/dabmux/fig/__init__.py` (+2 LOC)
   - Export FIG6_0 and FIG6_1

4. `src/dabmux/config/parser.py` (+30 LOC)
   - Parse `conditional_access` configuration
   - Parse `ca_system` per service

### Files to Create for Examples:
1. `examples/priority7_conditional_access.yaml` (~100 LOC)

---

## Important Notes

### What CA Does NOT Do

**This implementation only handles FIG signaling for CA.**

**NOT included (handled by external systems):**
- ✗ Content encryption/scrambling
- ✗ ECM (Entitlement Control Messages)
- ✗ EMM (Entitlement Management Messages)
- ✗ Smart card integration
- ✗ Key management
- ✗ Subscriber management

**Actual encryption is done by:**
- Dedicated CA hardware/software modules
- Content scrambling before multiplexing
- External CA systems (Nagravision, Viaccess, etc.)

**Our role:**
- ✓ Signal which CA systems are used (FIG 6/0)
- ✓ Signal which services require CA (FIG 6/1)
- ✓ Provide configuration interface

### Testing Limitations

- Cannot test actual decryption (requires CA hardware)
- Can only verify FIG encoding correctness
- Can test with etisnoop (FIG 6 decoding)
- Professional testing requires CA system integration

---

## Success Criteria

Implementation is complete when:

1. ✅ ConditionalAccessConfig dataclass added
2. ✅ FIG 6/0 implemented (CA organization)
3. ✅ FIG 6/1 implemented (CA service)
4. ✅ ~20 unit tests pass (10 for 6/0, 10 for 6/1)
5. ✅ FIG 6 types registered conditionally
6. ✅ Configuration schema extended
7. ✅ Example configuration provided
8. ✅ No regressions in existing tests

**Deliverables:**
- 2 new FIG implementations (6/0, 6/1)
- 1 new data structure (ConditionalAccessConfig)
- 1 new test file (~20 tests)
- Extended configuration schema
- Example configuration
- Updated exports

---

## Estimated Effort

| Phase | Task | Time | Tests |
|-------|------|------|-------|
| 1 | Data Model & Config | 1-2h | - |
| 2 | FIG 6/0 Implementation | 2-3h | 10 |
| 3 | FIG 6/1 Implementation | 2-3h | 10 |
| 4 | Integration | 1h | - |
| 5 | Testing & Examples | 1h | - |
| **Total** | **Priority 7 Complete** | **7-10h** | **~20** |

---

## Standards References

- **ETSI EN 300 401 Section 11:** Conditional Access
  - 11.2.1: FIG 6/0 (CA Organization)
  - 11.2.2: FIG 6/1 (CA Service)
  - 11.3: CA system identification

- **DVB Project:** CA system ID registry (CAId assignments)

---

## Next Steps After Priority 7

After successful implementation:
- **Priority 8:** Regional Services & Variants
- **Priority 9:** Quality & Compliance
- **Future:** Additional FIG types (FIG 0/4, 0/7, 0/11, etc.)

**Note:** Priority 7 completes the **security signaling** for DAB. Actual content protection requires external CA systems.
