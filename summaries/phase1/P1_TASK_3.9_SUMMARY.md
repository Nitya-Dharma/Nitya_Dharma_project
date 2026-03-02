# Task 3.9 - SEO Data Exposure Contract (Dynamic Placeholders) Summary

## Overview
Successfully documented and locked the SEO data exposure contract for the Nitya Dharma platform. This provides clear rules about dynamic, placeholder-based SEO that ensures every Pandit has unique, up-to-date metadata. **NO CODE was written** - this is contract locking only.

## Changes Made

### 1. Created SEO Data Exposure Contract Document
**File:** `SEO_DATA_EXPOSURE_CONTRACT.md` (newly created)

**Contents:**
- Why Pandit profiles must not have default static SEO values
- What placeholder-based SEO means in this system
- Which referral-related data may be exposed as placeholders
- Which data must never be exposed
- How moderation and trust visibility affect placeholder availability
- Which downstream modules consume this contract and how

**Purpose:**
- Ensure SEO is always dynamic and profile-specific
- Prevent duplicate metadata across Pandits
- Enable automatic SEO updates when profiles change
- Define clear data exposure boundaries

---

## Core Principle Documented

### No Default SEO Values

**Critical Principle:**
- ❌ **NO default SEO values for Pandit profiles**
- ✅ **SEO is always generated dynamically using placeholders**
- ✅ **Placeholders resolve using current Pandit profile data**

**Why This Matters:**
- Every Pandit has unique SEO metadata
- SEO updates automatically when profile updates
- No two profiles compete with identical metadata
- Prevents duplicate content penalties
- Ensures SEO reflects current, accurate information

**Contract:**
- ✅ SEO is always dynamic and profile-specific
- ✅ No static or default SEO values are stored
- ✅ Placeholders are resolved at render time
- ✅ SEO automatically reflects profile changes

---

## Placeholder-Based SEO System

### What Placeholders Mean

**Definition:**
Placeholders are tokens, not static strings. They represent dynamic data points resolved at render time.

**Placeholder Examples:**
- `{pandit_name}` - Pandit's display name
- `{city}` - City where Pandit operates
- `{local_area}` - Local area served
- `{pooja_types}` - Types of poojas performed
- `{experience_years}` - Years of experience
- `{referrer_name}` - Name of referring Pandit (only if visible)
- `{trust_depth}` - Trust chain depth

**Placeholder Characteristics:**
- ✅ Stored as templates (not resolved values)
- ✅ Resolved at render time (not at storage time)
- ✅ Always reflect current data
- ✅ Profile-specific (not global defaults)

**Contract:**
- ✅ Placeholders are tokens, not static strings
- ✅ Resolution happens at render time
- ✅ Placeholders always use current profile data

---

## Data Exposure Rules

### 1. Data That MAY Be Exposed (Read-Only, Placeholder-Only)

**Referral-Related Data:**
- Referrer display name (`{referrer_name}`)
- Referrer experience (`{referrer_experience_years}`)
- Trust chain depth (`{trust_depth}`)
- Referral relationship existence (`{has_referrer}`)

**Profile-Related Data (Context):**
- Pandit name, city, local area, pooja types, experience years, bio summary

**Data Characteristics:**
- ✅ All data is read-only
- ✅ All data is never hardcoded
- ✅ All data is never injected as defaults
- ✅ All data respects moderation rules

**Contract:**
- ✅ Referral data exposed only as placeholders
- ✅ Data is read-only and dynamic
- ✅ No hardcoded or default values

---

### 2. Data That MUST NOT Be Exposed

**Security-Sensitive Data:**
- ❌ Referral tokens
- ❌ Referral codes
- ❌ Internal IDs
- ❌ Referral usage counts
- ❌ Audit snapshot fields
- ❌ Moderation reasons

**Why:**
- Security risk if exposed
- Privacy concerns
- Not SEO-relevant
- Internal administrative data

**Contract:**
- ✅ Security-sensitive data is never exposed
- ✅ Internal audit data is never exposed
- ✅ Only SEO-safe, public data is exposed

---

## Moderation-Aware Placeholder Rules

### Trust Visibility Impact

**Fully Blocked Referrer:**
- ❌ `{referrer_name}` placeholder **NOT available**
- ❌ `{referrer_experience_years}` placeholder **NOT available**
- ❌ `{trust_depth}` placeholder **NOT available**
- ✅ `{has_referrer}` returns `false` (or placeholder not used)

**Limited Blocked Referrer:**
- ⚠️ `{referrer_name}` placeholder **available with warning flag**
- ⚠️ `{referrer_experience_years}` placeholder **available with warning flag**
- ⚠️ `{trust_depth}` placeholder **available with warning flag**
- ✅ Consumer modules decide how to render warning

**Active Referrer:**
- ✅ `{referrer_name}` placeholder **available normally**
- ✅ `{referrer_experience_years}` placeholder **available normally**
- ✅ `{trust_depth}` placeholder **available normally**
- ✅ No warnings or restrictions

**Contract:**
- ✅ Placeholder availability respects moderation state
- ✅ Fully blocked referrers → no referral placeholders
- ✅ Limited blocked referrers → placeholders with warning flag
- ✅ Active referrers → normal placeholder availability

---

## Downstream Module Consumption

### Module 4 — Pandit Profile
- ✅ Stores SEO templates with placeholders
- ✅ Defines placeholder availability
- ✅ Provides profile data for resolution

### Module 7 — Search & SEO Rendering
- ✅ Resolves placeholders at render time
- ✅ Generates final SEO metadata
- ✅ Creates structured data (Schema.org)
- ✅ Renders meta tags in HTML

### Module 10 — Public Trust Display
- ✅ Displays referral trust information
- ✅ Shows trust chain depth
- ✅ Renders trust badges

### Referral Module Responsibilities
- ✅ Exposes data as placeholders
- ✅ Respects moderation rules
- ✅ Provides read-only access
- ❌ Does NOT render SEO
- ❌ Does NOT generate meta tags
- ❌ Does NOT resolve placeholders

**Contract:**
- ✅ Referral module is data provider only
- ✅ Consumer modules handle rendering
- ✅ Clear separation of concerns

---

## Why No Default SEO Values

### Problems with Default SEO

**If Default SEO Values Were Allowed:**
- ❌ Multiple Pandits would have identical SEO
- ❌ Search engines penalize duplicate content
- ❌ SEO becomes outdated and misleading
- ❌ Manual SEO updates required
- ❌ Profiles compete with identical metadata

### Benefits of Placeholder-Based SEO

**With Placeholder-Based SEO:**
- ✅ Every Pandit has unique metadata
- ✅ SEO updates automatically when profile updates
- ✅ No manual maintenance required
- ✅ Works for any number of Pandits
- ✅ Consistent formatting

**Contract:**
- ✅ Placeholder-based SEO is mandatory
- ✅ SEO is always unique and current
- ✅ System scales automatically

---

## Placeholder Examples

### SEO Title Template Examples

**Example 1: Basic Profile**
```
Template: "Best {pooja_types} Pandit in {city}, {local_area} | {pandit_name}"
Resolved: "Best Puja, Homa Pandit in Mumbai, Andheri | Pandit Rao"
```

**Example 2: With Referrer (Active)**
```
Template: "Best {pooja_types} Pandit in {city} | Referred by {referrer_name} | {pandit_name}"
Resolved: "Best Puja Pandit in Mumbai | Referred by Pandit Sharma | Pandit Rao"
```

**Contract:**
- ✅ Templates use placeholders
- ✅ Resolution creates unique SEO
- ✅ Examples show dynamic nature

---

## Integration with Previous Modules

### Module 1 (User & Role System)
- ✅ Uses User model for Pandit identification
- ✅ Respects role system
- ✅ No User model changes

### Module 2 (Pandit Onboarding)
- ✅ Respects master data rules (Task 2.6)
- ✅ Uses approved master data only
- ✅ Suggested data not used in SEO

### Module 3 (This Module)
- ✅ Integrates with Task 3.7 (Trust Chain Visibility)
- ✅ Respects referral eligibility rules
- ✅ Uses audit data appropriately

---

## Validation Checklist

### Policy Correctness
- ✅ No default SEO values mentioned
- ✅ Placeholders clearly defined
- ✅ Referral data is read-only
- ✅ Moderation-aware exposure rules included
- ✅ No SEO rendering logic included

### Scope Compliance
- ✅ No code, models, or migrations suggested
- ✅ No UI or implementation details
- ✅ No SEO generation logic
- ✅ Contract definition only

---

## Rules Compliance

### ✅ Policy Only
- ✅ No code written
- ✅ No models defined
- ✅ No implementation details
- ✅ Documentation only

### ✅ Clear and Unambiguous
- ✅ Placeholder system is explicit
- ✅ Data exposure rules are clear
- ✅ Moderation impact is defined
- ✅ Downstream consumption is documented

### ✅ Integration Ready
- ✅ Policy aligns with previous modules
- ✅ Policy ready for Module 4 and Module 7
- ✅ No breaking changes
- ✅ Clear consumption guidelines

---

## Next Steps

**Task 3.9 is complete and locked.**

Ready to proceed to:
- **Module 3 → Task 3.10:** Referral × Master Data Suggestion Compatibility (NO CODE)

**Important:**
- SEO data exposure contract is documented and locked
- All future modules must respect this contract
- No code was written (documentation only)
- Placeholder-based SEO is mandatory

---

## Notes

- ✅ SEO data exposure contract is the single source of truth
- ✅ Placeholder system is clearly defined
- ✅ Moderation-aware rules are explicit
- ✅ No default SEO values are allowed
- ✅ No code was written (documentation only)
- ✅ Module 3 discipline maintained throughout
- ✅ Ready for Task 3.10 (Referral × Master Data Suggestion Compatibility)

---

**Status:** ✅ Task 3.9 Complete - SEO Data Exposure Contract (Dynamic Placeholders) Documented & Locked
**Module 3:** Task 3.9 COMPLETE
**Ready for:** Task 3.10 - Referral × Master Data Suggestion Compatibility (NO CODE)











