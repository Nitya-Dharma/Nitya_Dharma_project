# Task 3.8 - Referral Rate-Limiting Policy Summary

## Overview
Successfully documented and locked referral rate-limiting policy for the Nitya Dharma platform. This provides clear rules about rate limits for referral link generation and usage, preventing abuse and spam while ensuring fair usage. **NO CODE was written** - this is policy locking only.

## Changes Made

### 1. Created Rate-Limiting Policy Document
**File:** `REFERRAL_RATE_LIMITING_POLICY.md` (newly created)

**Contents:**
- Which referral-related actions must be rate-limited
- Why rate-limiting is required for trust and stability
- How rate limits should behave when exceeded
- Why rate-limiting must be separated from moderation logic
- Non-paid implementation constraints for future tasks

**Purpose:**
- Prevent abuse and spam of referral system
- Protect trust chain credibility
- Maintain onboarding stability
- Define limits before implementation

---

## Rate-Limiting Rules Documented

### 1. Referral Link Generation Limits

**What Must Be Limited:**
- Referral link generation per Admin Pandit
- Referral link generation per Super Admin
- Active referral links at a time

**Policy Example (Final Values Can Be Tuned Later):**
- Max referral links per admin per day: **10 links**
- Max active referral links at a time: **20 links**
- Time window: **24 hours** (rolling window)

**When Limit Exceeded:**
- ❌ New referral link generation is denied
- ✅ Existing links remain unaffected
- ❌ No auto-blocking occurs
- ✅ Clear error message returned

**Contract:**
- ✅ Generation limits are per admin
- ✅ Limits apply to time windows
- ✅ Existing links not affected
- ✅ No automatic blocking

---

### 2. Referral Usage Attempt Limits

**What Must Be Limited:**
- Referral usage attempts per IP address
- Referral usage attempts per referral token
- Registration attempts with invalid referral codes

**Policy Example (Final Values Can Be Tuned Later):**
- Max registration attempts per IP per hour: **5 attempts**
- Max invalid referral code attempts per IP per hour: **10 attempts**
- Time window: **1 hour** (rolling window)

**When Limit Exceeded:**
- ❌ Registration attempt is blocked temporarily
- ❌ Referral link is NOT invalidated
- ❌ No moderation action is triggered
- ✅ Clear error message returned

**Contract:**
- ✅ Usage limits are per IP and per token
- ✅ Limits apply to time windows
- ✅ Referral links remain valid
- ✅ No automatic moderation

---

### 3. Non-Paid Implementation Constraint

**Constraint:**
- Rate-limiting must **NOT** require paid services
- Must use free, open-source solutions
- Must be implementable with Django built-in features

**Allowed Implementation Approaches:**
- ✅ Django cache (in-memory or file-based)
- ✅ Database counters (simple count tables)
- ✅ Timestamp comparisons (query-based rate limiting)

**Not Allowed:**
- ❌ Paid rate-limiting services
- ❌ Third-party paid APIs
- ❌ External rate-limiting services

**Contract:**
- ✅ Rate-limiting uses free solutions only
- ✅ Django cache or database counters allowed
- ✅ No paid services required

---

## Why Rate-Limiting is Required

### 1. Trust Chain Credibility
- Prevents spam referral generation
- Maintains quality of referral network
- Protects trust chain integrity
- Ensures only legitimate referrals

### 2. Onboarding Stability
- Prevents system overload
- Maintains registration stability
- Ensures fair access to registration
- Protects database performance

### 3. Database Integrity
- Prevents excessive database writes
- Maintains database performance
- Protects against abuse
- Ensures data quality

**Contract:**
- ✅ Rate-limiting protects trust chain
- ✅ Maintains platform stability
- ✅ Ensures data quality

---

## Separation from Moderation

### Rate-Limiting vs. Moderation

**Rate-Limiting:**
- Technical safeguard
- Temporary restriction
- Does NOT imply misconduct
- Does NOT block Pandits permanently

**Moderation:**
- Administrative action
- Permanent or long-term restriction
- Implies misconduct or policy violation
- Blocks Pandits based on behavior

**Contract:**
- ✅ Rate-limiting ≠ Moderation
- ✅ Rate-limiting is technical only
- ✅ Moderation is administrative

---

### What Rate-Limiting Does NOT Do

**Rate-Limiting Does NOT:**
- ❌ Block Pandits permanently
- ❌ Trigger admin review
- ❌ Affect trust visibility
- ❌ Invalidate referral links
- ❌ Modify referral data
- ❌ Send notifications or alerts

**Contract:**
- ✅ Rate-limiting is non-destructive
- ✅ No permanent blocks
- ✅ No moderation actions
- ✅ No data modifications

---

## Implementation Guidelines (Future)

### Django Cache Approach
- Use Django cache to store attempt counts
- Key: `referral_generation_{admin_id}_{date}`
- Value: Count of attempts
- TTL: Time window duration

### Database Counters Approach
- Create simple counter table
- Track attempts per admin/IP per time window
- Query counts before allowing action
- Clean up old records periodically

### Timestamp Comparison Approach
- Query recent attempts from referral tables
- Count attempts within time window
- Compare count to limit
- Allow or deny based on count

**Contract:**
- ✅ Multiple implementation approaches allowed
- ✅ Free solutions only
- ✅ Simple implementation

---

## Integration with Previous Modules

### Module 1 (User & Role System)
- ✅ Uses User model for admin identification
- ✅ Role checks for generation limits
- ✅ No changes to User model

### Module 2 (Pandit Onboarding)
- ✅ Respects registration workflow
- ✅ Rate-limiting does not affect approval

### Module 3 (This Module)
- ✅ Applies to referral generation (Task 3.3)
- ✅ Applies to referral validation (Task 3.4)
- ✅ Separate from eligibility rules (Task 3.5)

### Module 12 (Security Hardening - Future)
- ✅ Will implement rate-limiting
- ✅ Policy guides implementation
- ✅ No paid services required

---

## Validation Checklist

### Policy Clarity
- ✅ Generation limits are clearly defined
- ✅ Usage limits are clearly defined
- ✅ Behavior when exceeded is clear
- ✅ Implementation constraints are defined

### Separation from Moderation
- ✅ Rate-limiting ≠ Moderation
- ✅ No automatic blocking
- ✅ No moderation actions
- ✅ Temporary restrictions only

### Implementation Constraints
- ✅ No paid services required
- ✅ Free solutions only
- ✅ Django cache or database allowed
- ✅ Simple implementation

---

## Rules Compliance

### ✅ Policy Only
- ✅ No code written
- ✅ No models defined
- ✅ No implementation details
- ✅ Documentation only

### ✅ Clear and Unambiguous
- ✅ Rate limits are explicit
- ✅ Behavior when exceeded is clear
- ✅ Implementation constraints are defined
- ✅ Separation from moderation is clear

### ✅ Integration Ready
- ✅ Policy aligns with previous modules
- ✅ Policy ready for Module 12 implementation
- ✅ No breaking changes
- ✅ Clear implementation guidelines

---

## Next Steps

**Task 3.8 is complete and locked.**

Ready to proceed to:
- **Module 3 → Task 3.9:** SEO Data Exposure Contract (NO CODE)

**Important:**
- Rate-limiting policy is documented and locked
- All future modules must respect this policy
- No code was written (documentation only)
- Implementation will be in Module 12

---

## Notes

- ✅ Rate-limiting policy is the single source of truth
- ✅ All rules are explicit and unambiguous
- ✅ Implementation constraints are clear
- ✅ Separation from moderation is defined
- ✅ No code was written (documentation only)
- ✅ Module 3 discipline maintained throughout
- ✅ Ready for Task 3.9 (SEO Data Exposure Contract)

---

**Status:** ✅ Task 3.8 Complete - Referral Rate-Limiting Policy Documented & Locked
**Module 3:** Task 3.8 COMPLETE
**Ready for:** Task 3.9 - SEO Data Exposure Contract (NO CODE)











