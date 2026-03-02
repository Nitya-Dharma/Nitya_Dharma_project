# Task 3.7 - Trust Chain Visibility Rules Summary

## Overview
Successfully documented and locked trust chain visibility rules for the Nitya Dharma platform. This provides clear rules about when and how the "Referred by" trust label is displayed publicly based on referrer moderation state. **NO CODE was written** - this is display and policy locking only.

## Changes Made

### 1. Created Trust Chain Visibility Rules Document
**File:** `TRUST_CHAIN_VISIBILITY_RULES.md` (newly created)

**Contents:**
- When referral trust should be displayed normally
- When it should be displayed with a warning
- When it should be hidden completely
- How referrer moderation states affect visibility
- Why trust visibility rules must be separated from referral logic

**Purpose:**
- Define visibility rules for trust chain display
- Ensure trust remains transparent
- Respect moderation decisions
- Provide clear rules for consuming modules

---

## Trust Chain Visibility Rules Documented

### 1. Normal Display (Active Referrer)

**Conditions (ALL Must Be Met):**
- ✅ Referrer `status='active'` (approved and active)
- ✅ Referrer `is_active=True` (can authenticate)
- ✅ Referrer is **NOT** limited blocked
- ✅ Referrer is **NOT** fully blocked

**Display Format:**
- ✅ "Referred by: Pandit [Name] ([Experience] years experience)"
- ✅ No warnings
- ✅ No badges
- ✅ Normal trust display

**Contract:**
- ✅ Active referrers display normally
- ✅ No warnings or badges
- ✅ Full trust information shown

---

### 2. Limited Blocked Referrer (Warning Display)

**Conditions:**
- ⚠️ Referrer is **limited blocked** (temporarily restricted)
- ⚠️ Referrer is under review
- ⚠️ Referrer is temporarily restricted by admin

**Display Format:**
- ⚠️ "Referred by: Pandit [Name] (Under Review)"
- ⚠️ Warning badge displayed
- ⚠️ Trust chain still visible

**Contract:**
- ✅ Limited blocked referrers display with warning
- ✅ Trust chain remains visible
- ✅ Warning is clear but non-accusatory

---

### 3. Fully Blocked Referrer (Hidden Display)

**Conditions:**
- ❌ Referrer is **fully blocked** by Super Admin
- ❌ Referrer has been permanently restricted

**Display Format:**
- ❌ "Referred by" section is completely hidden
- ❌ No placeholder text
- ❌ No warnings shown publicly
- ❌ No trust information displayed

**Contract:**
- ✅ Fully blocked referrers → Trust display hidden
- ✅ No placeholder text shown
- ✅ Complete hiding of trust information

---

## How Referrer Moderation States Affect Visibility

### Status-Based Visibility

**Referrer Status = 'active':**
- ✅ Display normally (if not blocked)

**Referrer Status = 'pending':**
- ❌ Do not display (referrer not approved yet)

**Referrer Status = 'rejected':**
- ❌ Do not display (referrer rejected)

**Contract:**
- ✅ Only active referrers display trust chain
- ✅ Pending/rejected referrers do not display
- ✅ Status check is mandatory

---

### Block State-Based Visibility

**Block State = 'none':**
- ✅ Display normally (if status='active')

**Block State = 'limited_blocked':**
- ⚠️ Display with warning badge

**Block State = 'fully_blocked':**
- ❌ Hide completely

**Contract:**
- ✅ Block state determines visibility
- ✅ Limited blocked shows with warning
- ✅ Fully blocked hides completely

---

## Why Trust Visibility Rules Must Be Separated from Referral Logic

### 1. Separation of Concerns

**Referral Logic (Tasks 3.1-3.6):**
- Referral generation
- Referral validation
- Referral usage tracking
- Trust chain data storage

**Trust Visibility (Task 3.7):**
- Public display rules
- Visibility based on moderation
- Warning badges
- Display formatting

**Contract:**
- ✅ Referral logic ≠ Trust visibility
- ✅ Data storage ≠ Display rules
- ✅ Clean separation of concerns

---

### 2. Non-Destructive Display

**Trust Visibility:**
- Does not modify referral data
- Does not affect referral validity
- Does not change trust chain relationships
- Only affects public display

**Contract:**
- ✅ Trust visibility is non-destructive
- ✅ Data remains unchanged
- ✅ Only display is affected

---

### 3. Module Integration

**Consuming Modules:**
- Module 4 (Pandit Profile) - Displays trust chain on profiles
- Module 7 (Search & SEO) - Includes trust in search results
- Module 10 (Public Trust Display) - Public trust display implementation

**Contract:**
- ✅ Visibility rules are consumed by other modules
- ✅ Rules are not implemented in Module 3
- ✅ Clear contract for consuming modules

---

## Display Rules Summary

### Visibility Decision Matrix

| Referrer State | Status | is_active | Block State | Visibility |
|----------------|--------|-----------|-------------|------------|
| Active | 'active' | True | 'none' | ✅ Display normally |
| Limited Blocked | 'active' | True | 'limited_blocked' | ⚠️ Display with warning |
| Fully Blocked | 'active' | True | 'fully_blocked' | ❌ Hide completely |
| Pending | 'pending' | False | 'none' | ❌ Hide (not approved) |
| Rejected | 'rejected' | False | 'none' | ❌ Hide (rejected) |
| Inactive | 'active' | False | 'none' | ❌ Hide (inactive) |

**Contract:**
- ✅ Clear visibility rules for each state
- ✅ Decision matrix is unambiguous
- ✅ All states are covered

---

## Integration with Previous Modules

### Module 1 (User & Role System)
- ✅ Uses User model status field
- ✅ Uses User model is_active flag
- ✅ Uses User model role field

### Module 2 (Pandit Onboarding)
- ✅ Respects approval workflow
- ✅ Respects status transitions

### Module 3 (This Module)
- ✅ Integrates with referral strategy (Task 3.1)
- ✅ Uses referral models (Task 3.2)
- ✅ Respects eligibility rules (Task 3.5)
- ✅ Uses audit snapshot data (Task 3.6)

### Module 11 (Admin Governance - Future)
- ✅ Will integrate with blocking workflow
- ✅ Block states affect visibility
- ✅ Rules ready for Module 11

---

## Implementation Guidelines for Consuming Modules

### Module 4 (Pandit Profile)
- ✅ Must check referrer status, is_active, and block state
- ✅ Must apply visibility rules
- ✅ Must use correct display formats

### Module 7 (Search & SEO)
- ✅ Must check same state checks
- ✅ Must apply visibility rules in search results
- ✅ Must include trust only if visible

### Module 10 (Public Trust Display)
- ✅ Must implement trust display
- ✅ Must implement warning badges
- ✅ Must implement complete hiding

**Contract:**
- ✅ All consuming modules must respect visibility rules
- ✅ State checks are mandatory
- ✅ Display formats must match rules

---

## Validation Checklist

### Visibility Rules
- ✅ Active referrer → Display normally
- ✅ Limited blocked referrer → Display with warning
- ✅ Fully blocked referrer → Hide completely
- ✅ Pending/rejected referrer → Hide (not approved)

### Display Formats
- ✅ Normal display format defined
- ✅ Warning display format defined
- ✅ Hidden display format defined
- ✅ All formats are unambiguous

### State Checks
- ✅ Status check is mandatory
- ✅ is_active check is mandatory
- ✅ Block state check is mandatory
- ✅ Combined state determines visibility

### Integration
- ✅ Rules align with previous modules
- ✅ Rules ready for consuming modules
- ✅ No breaking changes
- ✅ Clear contract for implementation

---

## Rules Compliance

### ✅ Policy Only
- ✅ No code written
- ✅ No models defined
- ✅ No templates created
- ✅ Documentation only

### ✅ Clear and Unambiguous
- ✅ Visibility rules are explicit
- ✅ Display formats are defined
- ✅ State checks are mandatory
- ✅ Decision matrix is clear

### ✅ Integration Ready
- ✅ Rules align with previous modules
- ✅ Rules ready for consuming modules
- ✅ No breaking changes
- ✅ Clear implementation guidelines

---

## Next Steps

**Task 3.7 is complete and locked.**

Ready to proceed to:
- **Module 3 → Task 3.8:** Referral Rate-Limiting Policy (NO CODE)

**Important:**
- Trust chain visibility rules are documented and locked
- All future modules must respect these rules
- No code was written (documentation only)

---

## Notes

- ✅ Trust chain visibility rules are the single source of truth
- ✅ All rules are explicit and unambiguous
- ✅ Display formats are clearly defined
- ✅ State checks are mandatory
- ✅ No code was written (documentation only)
- ✅ Module 3 discipline maintained throughout
- ✅ Ready for Task 3.8 (Referral Rate-Limiting Policy)

---

**Status:** ✅ Task 3.7 Complete - Trust Chain Visibility Rules Documented & Locked
**Module 3:** Task 3.7 COMPLETE
**Ready for:** Task 3.8 - Referral Rate-Limiting Policy (NO CODE)











