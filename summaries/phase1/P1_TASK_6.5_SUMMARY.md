# Task 6.5 - Pooja-Specific Availability Rules Summary

## Overview
Successfully documented how availability may vary by pooja type, without turning availability into a booking or pricing system. This is a **policy and architecture document only** - no code, no models, no implementation. The document ensures Pandits can express capability-based availability, search can filter availability by pooja, and no pooja becomes a booking constraint.

---

## Task Type
**NO CODE** - Rules & Semantics Only

---

## Document Created

### File: `POOJA_SPECIFIC_AVAILABILITY_RULES.md`

**Purpose:**
- Define what pooja-specific availability represents
- Define how Pandits may associate availability with poojas
- Define what this availability must never imply
- Define how search may safely consume this signal
- Define hard boundaries that prevent booking or pricing logic

---

## Key Definitions

### Pooja-Specific Availability — Concept (LOCKED)

**Pooja-Specific Availability Means:**
- A Pandit may be available for certain poojas at certain times
- Availability reflects readiness, not acceptance

**📌 Example (conceptual):**
- Morning: Available for Abhishekam
- Evening: Available for Gruha Pravesh
- (This is not a booking promise.)

**📌 Availability reflects readiness, not acceptance.**

---

## Allowed Rules

**Pandit MAY:**
1. Associate availability entries with one or more poojas
2. Have different availability windows for different poojas
3. Update pooja availability anytime

**📌 Pandits have full control over pooja-specific availability.**

---

## Disallowed Rules

**Pooja-Specific Availability MUST NOT:**
- ❌ Imply confirmation
- ❌ Enforce duration
- ❌ Attach pricing
- ❌ Reserve time slots
- ❌ Affect trust, SEO, or ranking

**📌 Pooja availability is descriptive only — no transactional, pricing, or ranking logic.**

---

## Hard Boundaries (LOCKED)

**Pooja Availability Rules:**
- Pooja availability is advisory
- Final acceptance happens outside availability
- Search may filter, but not decide

**📌 Pooja availability is advisory — acceptance and booking are separate.**

---

## Module Dependencies

### Pooja-Specific Availability DEPENDS ON:
- Module 2 — Pooja Master Data (approved only)
- Module 4 — Profile Context

### Pooja-Specific Availability is CONSUMED BY:
- Module 7 — Search & Filters (read-only)
- Module 5 — Dashboards (read-only)

**📌 Pooja availability is consumed read-only — no mutation by consumers.**

---

## Key Conceptual Distinctions

- **"Pooja Availability" ≠ "Pooja Booking"** - Availability is declared readiness, booking is confirmed
- **"Pooja Readiness" ≠ "Pooja Acceptance"** - Readiness is capability, acceptance is confirmation
- **"Pooja Filter" ≠ "Pooja Constraint"** - Filter is search capability, constraint is booking requirement
- **"Pooja Association" ≠ "Pooja Pricing"** - Association is availability link, pricing is payment

**These distinctions prevent confusion with booking, pricing, or enforcement logic.**

---

## Why Pooja-Specific Rules Are Defined Before Implementation

### Architectural Reasons:
1. **Prevent Booking Confusion** - Clear separation from booking logic
2. **Prevent Pricing Logic Leakage** - No pricing in availability
3. **Maintain Search Flexibility** - Search can filter, not decide
4. **Future-Proof Design** - Pooja rules can evolve
5. **Prevent Scope Creep** - Clear boundaries

### Practical Benefits:
- ✅ No booking confusion
- ✅ No pricing logic leakage
- ✅ Search flexibility maintained
- ✅ Future-proof design
- ✅ Clear boundaries

---

## Pooja Availability Principles

1. **Advisory, Not Authoritative** - Pooja availability is advisory
2. **Readiness, Not Acceptance** - Availability reflects readiness
3. **Search Filter, Not Decision Maker** - Search can filter, not decide
4. **No Pricing or Duration** - No pricing or duration in availability
5. **Approved Poojas Only** - Only approved poojas from Module 2

---

## Validation Checklist

✅ **Pooja availability is advisory only**
✅ **No booking or pricing logic**
✅ **Search can filter, not decide**
✅ **Approved poojas only**
✅ **No code references exist**

---

## Common Cursor Failures (Prevented)

❌ Implements booking constraints
❌ Implements pricing logic
❌ Implements duration enforcement
❌ Allows suggested poojas
❌ Makes availability a booking requirement

**All of these are explicitly prevented by this document.**

---

## Why This Task Is Critical

### Without This Lock:
❌ Booking logic leaks into availability
❌ Pricing logic leaks into availability
❌ Search becomes decision maker

### With This Lock:
✅ Clear separation from booking
✅ No pricing logic leakage
✅ Search remains read-only

---

## Integration with Existing Modules

### Module 1 (User & Role System)
- ✅ Pooja availability respects Pandit role
- ✅ Role-based access control

### Module 2 (Master Data)
- ✅ Pooja availability uses approved poojas only
- ✅ No suggested/unapproved poojas

### Module 4 (Pandit Profile)
- ✅ Pooja availability linked to profile
- ✅ Profile provides context

### Module 5 (Dashboards)
- ✅ Dashboards display pooja availability (read-only)

### Module 6 (Availability) - THIS MODULE
- ✅ Defines pooja-specific availability rules
- ✅ Establishes advisory-only principle

### Future Modules
- ✅ Module 7 (Search & Filters) - Filter by pooja availability
- ✅ Module 8 (Booking Intent) - Separate from pooja availability

---

## Files Created

1. **`POOJA_SPECIFIC_AVAILABILITY_RULES.md`**
   - Complete pooja-specific availability rules
   - Policy and architecture document
   - No code, no models, no implementation

---

## Verification Results

### ✅ Scope Compliance
- **Status:** PASS
- **No Models:** Confirmed
- **No Migrations:** Confirmed
- **No Views/APIs:** Confirmed
- **No Templates:** Confirmed
- **No Code:** Confirmed

### ✅ Policy Documentation
- **Status:** PASS
- **Pooja Rules Defined:** ✅
- **Hard Boundaries Locked:** ✅
- **Key Distinctions Provided:** ✅
- **Module Dependencies Documented:** ✅

### ✅ Architectural Alignment
- **Status:** PASS
- **Aligned with Task 6.1 (Strategy):** ✅
- **Aligned with Task 6.2 (Data Model):** ✅
- **Aligned with Module 2 (Master Data):** ✅
- **Ready for Task 6.6 (City & Area Context):** ✅

---

## Rules Compliance

### ✅ NO CODE Principle
- ✅ No Django models created
- ✅ No migrations created
- ✅ No views or APIs created
- ✅ No templates created
- ✅ Pure policy and architecture document

### ✅ Clear and Unambiguous
- ✅ Pooja rules clearly defined
- ✅ Hard boundaries explicitly stated
- ✅ Key distinctions provided
- ✅ Module dependencies documented

### ✅ Architectural Alignment
- ✅ Aligned with all previous Module 6 tasks
- ✅ Aligned with Module 2 (Master Data)
- ✅ Ready for Task 6.6
- ✅ Clear separation from booking/pricing

---

## Next Steps

**Task 6.5 is complete and locked.**

Ready to proceed to:
- **Module 6 → Task 6.6:** City & Area Context for Availability (NO CODE)

**Important:**
- Pooja-specific availability rules are documented and locked
- Advisory-only principle established
- No booking or pricing logic
- Foundation is stable and ready for Task 6.6

---

## Notes

- ✅ Pooja-specific availability rules are locked before any implementation
- ✅ Availability is advisory, not authoritative
- ✅ Only approved poojas allowed
- ✅ No booking or pricing logic
- ✅ No code was written (policy document only)

---

**Status:** ✅ Task 6.5 Complete & Locked - Pooja-Specific Availability Rules Documented  
**Module 6:** Task 6.5 COMPLETE  
**Type:** Policy & Architecture Document (NO CODE)  
**Ready for:** Task 6.6 - City & Area Context for Availability (NO CODE)









