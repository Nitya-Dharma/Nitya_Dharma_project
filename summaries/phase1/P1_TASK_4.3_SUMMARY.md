# Task 4.3 - Pandit Profile Media Strategy & Safety Rules Summary

## Overview
Successfully documented the media strategy and safety rules for Pandit Profiles. This is a **policy and architecture document only** - no code, no models, no implementation. The document locks media responsibility boundaries before any upload or storage system is introduced.

---

## Task Type
**NO CODE** - Strategy, Policy & Boundaries Only

---

## Document Created

### File: `PANDIT_PROFILE_MEDIA_STRATEGY.md`

**Purpose:**
- Define what types of media a Pandit Profile may display
- Define what the profile is responsible for regarding media
- Define what the profile must NEVER do
- Define which modules handle upload, storage, moderation, and visibility
- Explain why media is treated as a consumer-only concern in the profile

---

## Key Definitions

### Media Types (Allowed - Display Only)

1. **Profile Picture** - Primary identity image (optional)
2. **Banner / Cover Image** - Header image (optional)
3. **Gallery Images** - Limited set of showcase images (optional)
4. **Embedded Video Links** - External video URLs (optional)

**Important:** No media type is mandatory. Absence of media must not block profile visibility.

---

## Media Ownership & Control

### ✅ What the Pandit Profile DOES

- Displays approved media
- Orders and groups media for presentation
- Respects visibility & moderation decisions

### ❌ What the Pandit Profile NEVER DOES

- Upload files
- Store files
- Resize / compress images
- Validate file type or size
- Moderate content
- Decide approval or rejection
- Handle abuse or reports

**The profile is a pure consumer of media, not a producer or controller.**

---

## Media Responsibility Split (LOCKED)

| Concern | Owner Module |
|---------|--------------|
| File upload | Future Media Module |
| Storage (local / S3 / CDN) | Future Media Module |
| File validation | Future Media Module |
| Virus / abuse checks | Module 11 (Governance) |
| Media approval / rejection | Module 11 (Governance) |
| Visibility enforcement | Module 11 (Governance) |
| Rendering media | Module 7 (Search / Public Pages) |
| Profile composition | Module 4 (THIS MODULE) |

---

## Hard Safety Rules (LOCKED)

❌ **Media must NEVER:**

1. Be stored directly in PanditProfile
2. Bypass governance checks
3. Be visible if Pandit is blocked
4. Be visible if media is unapproved
5. Be trusted for identity verification
6. Affect trust score or ranking
7. Influence search relevance directly

---

## Media & Visibility Interaction

**Key Principle:**
- Media visibility is binary input to the profile: Show or Hide
- No logic lives in the profile model
- Profile is a pure consumer of governance decisions

**Visibility Control:**
- If Pandit is blocked → Media hidden (governance-controlled)
- If media is unapproved → Media hidden
- If media is approved → Profile may display (governance-controlled)

---

## Module Dependencies

### Profile Media DEPENDS ON:
- Future Media Module (uploads, storage, validation)
- Module 11 — Governance & Moderation (approval, visibility)
- Module 7 — Rendering Rules (HTML generation)

### Profile Media is CONSUMED BY:
- Module 7 — Public Profile Rendering
- Module 10 — Trust Display (visual only)
- Module 5 — Dashboards (editing UI later)

---

## Why Media is Consumer-Only in Profile

### Architectural Reasons:
1. **Separation of Concerns** - Profile = display, Media = upload/storage
2. **Security** - Upload logic must be centralized and audited
3. **Scalability** - Storage decisions are infrastructure-level
4. **Governance Authority** - Moderation must be centralized
5. **Future Flexibility** - Media requirements may change independently

### Practical Benefits:
- ✅ Profile model stays clean and focused
- ✅ Media logic can evolve independently
- ✅ Governance remains authoritative
- ✅ No refactoring needed when media requirements change
- ✅ Clear ownership and responsibility

---

## Data Model Implications (Future)

### What Profile Model Will NOT Contain:
❌ No ImageField or FileField
❌ No Media Validation Fields
❌ No Media Storage Configuration

### What Future Media Module Will Contain:
✅ Separate Media Model (links to PanditProfile)
✅ Media Storage Configuration
✅ File references and approval status

**Profile model remains clean and focused on profile data only.**

---

## Validation Checklist

✅ **PanditProfile stores no files**
✅ **Media moderation is external**
✅ **Media visibility is governed, not decided here**
✅ **Media does not affect trust or SEO directly**
✅ **No upload or validation logic exists**
✅ **No code references exist**

---

## Common Cursor Failures (Prevented)

❌ Adds ImageField / FileField to PanditProfile
❌ Mentions S3 / media storage configuration
❌ Adds file validation rules
❌ Adds moderation flags
❌ Connects media to ranking or trust
❌ Implements upload UI

**All of these are explicitly prevented by this document.**

---

## Why This Task Is Critical

### Without This Lock:
❌ Profiles become security liabilities
❌ Media bypasses moderation
❌ Storage decisions leak everywhere
❌ Abuse becomes unmanageable

### With This Lock:
✅ Clean isolation
✅ Safe extensibility
✅ Zero refactors later
✅ Governance remains authoritative

---

## Integration with Existing Modules

### Module 1 (User & Role System)
- ✅ Profile media respects user role and status
- ✅ Media visibility respects user.is_active

### Module 2 (Pandit Onboarding)
- ✅ Media is not part of onboarding
- ✅ Media can be added after approval

### Module 3 (Referral & Trust Chain)
- ✅ Media does not affect referral logic
- ✅ Media is decorative only

### Module 4 (Pandit Profile) - THIS MODULE
- ✅ Profile displays approved media
- ✅ Profile does not handle uploads
- ✅ Profile respects governance decisions

### Future Modules
- ✅ Module 5 (Dashboards) - Media management via Media Module
- ✅ Module 7 (Search & SEO) - Media for display only
- ✅ Module 11 (Governance) - Media approval and visibility control

---

## Files Created

1. **`PANDIT_PROFILE_MEDIA_STRATEGY.md`**
   - Complete media strategy and safety rules
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
- **Media Types Defined:** ✅
- **Ownership Clarified:** ✅
- **Safety Rules Locked:** ✅
- **Module Dependencies Documented:** ✅

### ✅ Architectural Alignment
- **Status:** PASS
- **Aligned with Task 4.1 (Profile Strategy):** ✅
- **Aligned with Task 4.2 (Data Model):** ✅
- **Ready for Task 4.4 (SEO Editing Rules):** ✅

---

## Rules Compliance

### ✅ NO CODE Principle
- ✅ No Django models created
- ✅ No migrations created
- ✅ No views or APIs created
- ✅ No templates created
- ✅ Pure policy and architecture document

### ✅ Clear and Unambiguous
- ✅ Media types clearly defined
- ✅ Ownership boundaries clearly established
- ✅ Safety rules explicitly stated
- ✅ Module dependencies documented

### ✅ Architectural Alignment
- ✅ Aligned with Task 4.1 (Profile Strategy)
- ✅ Aligned with Task 4.2 (Data Model)
- ✅ Ready for future Media Module
- ✅ Ready for Module 11 (Governance)

---

## Next Steps

**Task 4.3 is complete and locked.**

Ready to proceed to:
- **Module 4 → Task 4.4:** Pandit Profile SEO Editing Interface Rules (NO CODE)

**Important:**
- Media strategy is documented and locked
- Profile boundaries are clear
- Module ownership is established
- Safety rules are defined
- Foundation is stable and ready for Task 4.4

---

## Notes

- ✅ Media strategy is locked before any implementation
- ✅ Profile model will remain clean (no media fields)
- ✅ Future Media Module will handle all upload/storage logic
- ✅ Module 11 (Governance) will control all moderation
- ✅ Profile is a pure consumer of approved media
- ✅ No code was written (policy document only)

---

**Status:** ✅ Task 4.3 Complete & Locked - Pandit Profile Media Strategy & Safety Rules Documented  
**Module 4:** Task 4.3 COMPLETE  
**Type:** Policy & Architecture Document (NO CODE)  
**Ready for:** Task 4.4 - Pandit Profile SEO Editing Interface Rules (NO CODE)









