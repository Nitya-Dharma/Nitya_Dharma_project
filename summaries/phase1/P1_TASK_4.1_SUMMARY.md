# Task 4.1 - Pandit Profile Strategy & Boundaries Summary

## Overview
Successfully documented and locked the Pandit Profile strategy and boundaries for the Nitya Dharma platform. This provides clear rules about what the Profile module is responsible for, what data it consumes, what it must never do, and how it integrates with other modules. **NO CODE was written** - this is strategy and contract locking only.

## Changes Made

### 1. Created Pandit Profile Strategy Document
**File:** `PANDIT_PROFILE_STRATEGY.md` (newly created)

**Contents:**
- What a Pandit Profile IS (consumer, not authority)
- What a Pandit Profile OWNS (structure, display, editing interface)
- What a Pandit Profile NEVER DOES (hard boundaries)
- Profile data ownership (consumed vs editable)
- Explicit module dependencies
- Visibility rules (declarative only)
- Integration with previous modules
- Future module requirements

**Purpose:**
- Lock responsibility and scope before implementation
- Prevent logic leakage into other modules
- Ensure clean separation of concerns
- Prepare for safe extensibility

---

## Core Strategy Documented

### 1. Profile as Consumer, Not Authority

**Fundamental Principle:**
- ✅ Profile is a consumer - displays and organizes data
- ✅ Profile is NOT an authority - never validates, approves, or enforces
- ✅ Profile is a composition - combines data from multiple modules

**Why:**
- Prevents tight coupling
- Ensures governance remains centralized
- Allows clean extensibility
- Maintains architectural integrity

**Contract:**
- ✅ Profile consumes data from other modules
- ✅ Profile never validates or enforces rules
- ✅ Profile respects external governance decisions

---

### 2. What a Pandit Profile IS

**A Pandit Profile is:**
- A read-only public representation of a Pandit's approved data
- Enriched by trust, SEO placeholders, media, and reviews
- All governed externally by other modules
- A composition of multiple modules working together

**It is NOT:**
- ❌ An authority that makes decisions
- ❌ A validator that checks data
- ❌ A moderator that controls content
- ❌ A rule engine that enforces policies

**Contract:**
- ✅ Profile is a presentation layer
- ✅ Profile reflects decisions made elsewhere
- ✅ Profile never makes decisions

---

### 3. What a Pandit Profile OWNS

**Profile owns:**
- ✅ Profile structure (sections, organization)
- ✅ Which data is displayed
- ✅ Which data is editable by Pandit
- ✅ Which data is read-only
- ✅ Profile completion criteria (informational only)

**Profile does not own:**
- ❌ Validation logic
- ❌ Enforcement logic
- ❌ Business rules
- ❌ Governance decisions

**Contract:**
- ✅ Profile owns structure and presentation
- ✅ Profile owns editing interface rules
- ✅ Profile does not own validation or enforcement

---

### 4. What a Pandit Profile NEVER DOES

**Hard Boundaries (LOCKED):**

1. **Approval & Validation**
   - ❌ Approve anything
   - ❌ Validate referral links
   - ❌ Validate master data
   - ❌ Validate media content

2. **SEO & Search**
   - ❌ Generate SEO metadata
   - ❌ Resolve SEO placeholders
   - ❌ Decide indexing rules
   - ❌ Influence search ranking

3. **Trust & Referral**
   - ❌ Calculate trust scores
   - ❌ Decide trust visibility
   - ❌ Validate referral relationships

4. **Moderation & Governance**
   - ❌ Moderate content
   - ❌ Decide visibility rules
   - ❌ Handle reports or appeals
   - ❌ Override governance decisions

5. **Access Control**
   - ❌ Perform access control
   - ❌ Enforce permissions
   - ❌ Bypass moderation rules

**Contract:**
- ✅ All boundaries are non-negotiable
- ✅ Profile is strictly a consumer
- ✅ All authority remains in other modules

---

### 5. Profile Data Ownership

**Data the Profile CONSUMES (Read-Only):**
- Pandit name, experience → Module 1 / Module 2
- Cities, areas, poojas → Module 2 (approved only)
- Referral trust → Module 3
- Trust visibility rules → Task 3.7
- SEO placeholders → Task 3.9
- Reviews → Module 9
- Media → Future Media Module
- Governance decisions → Module 11

**Data the Profile MAY EDIT (Later Tasks):**
- Bio / description
- Profile picture (upload interface)
- Banner image (upload interface)
- Gallery uploads (upload interface)
- YouTube links
- SEO template text (placeholders only)

**Contract:**
- ✅ Profile never validates or modifies consumed data
- ✅ Profile provides editing UI only
- ✅ All enforcement happens externally

---

### 6. Explicit Module Dependencies

**Profile DEPENDS ON:**
- ✅ Module 2 — Approved master data only
- ✅ Module 3 — Referral trust & visibility rules
- ✅ Module 9 — Reviews (display-only)
- ✅ Module 11 — Governance decisions
- ✅ Module 7 — Search rendering
- ✅ Task 3.9 — SEO placeholder contract

**Profile is CONSUMED BY:**
- ✅ Module 7 — Search & SEO
- ✅ Module 10 — Public Trust Display
- ✅ Module 5 — Dashboards

**Contract:**
- ✅ Profile consumes data from source modules
- ✅ Profile provides data to consuming modules
- ✅ Profile never modifies source data

---

### 7. Visibility Rules (Declarative Only)

**Guest Users:**
- ❌ Cannot see reviews
- ✅ See "Login to view reviews" CTA
- ❌ Cannot see SEO template text
- ❌ Cannot see profile completion status

**Blocked Pandits:**
- Visibility controlled by Module 11
- Profile obeys decisions — never decides

**Referral Trust:**
- Shown / hidden strictly via Task 3.7
- Profile only renders what it is told

**Contract:**
- ✅ Visibility rules are declarative
- ✅ Enforcement happens in other modules
- ✅ Profile respects visibility decisions

---

## Integration with Previous Modules

### Module 1 (User & Role System)
- ✅ Uses User model for identity
- ✅ Respects role and status
- ✅ Never modifies user data

### Module 2 (Pandit Onboarding & Master Data)
- ✅ Uses only approved master data
- ✅ Never shows suggested (unapproved) data
- ✅ Respects master data usage contract

### Module 3 (Referral & Trust Chain)
- ✅ Respects trust visibility rules
- ✅ Never generates or modifies trust data
- ✅ Stores SEO templates only (no resolution)

---

## Future Module Requirements

### Module 5 (Dashboards)
- ✅ Will consume profile data for editing interface
- ✅ Will respect profile boundaries
- ✅ Will never override profile rules

### Module 7 (Search & SEO)
- ✅ Will consume profile data for search results
- ✅ Will resolve SEO templates
- ✅ Will render profile pages

### Module 9 (Reviews)
- ✅ Will provide review data for display
- ✅ Will provide review visibility rules

### Module 11 (Governance)
- ✅ Will provide visibility decisions
- ✅ Will provide blocking decisions
- ✅ Profile will respect all governance decisions

**Contract:**
- ✅ All future modules will respect profile boundaries
- ✅ Profile will remain a consumer, not an authority
- ✅ Clean integration points are defined

---

## Validation Checklist

### Policy Correctness
- ✅ Profile does not own trust logic
- ✅ Profile does not generate SEO
- ✅ Profile uses approved master data only
- ✅ Suggested data is excluded
- ✅ Reviews are display-only
- ✅ Media moderation is external
- ✅ No code references exist

### Scope Compliance
- ✅ No models, migrations, or views suggested
- ✅ No UI or implementation details
- ✅ No SEO generation logic
- ✅ Policy definition only

---

## Rules Compliance

### ✅ Policy Only
- ✅ No code written
- ✅ No models defined
- ✅ No implementation details
- ✅ Documentation only

### ✅ Clear and Unambiguous
- ✅ Profile role is explicit (consumer, not authority)
- ✅ Boundaries are clearly defined
- ✅ Dependencies are documented
- ✅ Integration points are clear

### ✅ Architectural Alignment
- ✅ Aligned with Module 1 (User & Role System)
- ✅ Aligned with Module 2 (Pandit Onboarding)
- ✅ Aligned with Module 3 (Referral & Trust Chain)
- ✅ Ready for Module 5, 7, 9, 10, 11

---

## Why This Task Is Critical

**Without this lock:**
- Profiles become god-objects with too much responsibility
- Trust & SEO logic leaks everywhere
- Cursor AI creates tight coupling
- Governance becomes impossible
- System becomes fragile

**With this lock:**
- Clean layering between modules
- Safe extensibility
- No future refactors needed
- Predictable system behavior
- Maintainable architecture

---

## Next Steps

**Task 4.1 is complete and locked.**

Ready to proceed to:
- **Module 4 → Task 4.2:** Pandit Profile Core Data Model & Ownership (MODELS ONLY)

**Important:**
- Pandit Profile strategy is documented and locked
- All future modules must respect these contracts
- No code was written (documentation only)
- Profile boundaries are clear and non-negotiable

---

## Notes

- ✅ Profile strategy is the single source of truth
- ✅ All rules are explicit and unambiguous
- ✅ Future modules have clear requirements
- ✅ No code was written (documentation only)
- ✅ Module 4 discipline maintained throughout
- ✅ Foundation is stable and ready for Task 4.2

---

**Status:** ✅ Task 4.1 Complete - Pandit Profile Strategy & Boundaries Documented & Locked
**Module 4:** Task 4.1 COMPLETE
**Ready for:** Task 4.2 - Pandit Profile Core Data Model & Ownership (MODELS ONLY)









