# Task 9.4 — Review Model Definition — Summary

**Module:** 9 — Ratings & Reviews  
**Task Type:** Data Architecture (MODELS ONLY)  
**Status:** ✅ COMPLETE & LOCKED  
**Completion Date:** [Current Date]

---

## 📋 TASK OVERVIEW

**Task 9.4** defines the **minimal data contract** required to store a user review, following the "MODELS ONLY" principle with no business logic, workflows, or enforcement.

**Core Principle:** Schema definition only. Content is immutable, visibility state is mutable.

---

## ✅ DELIVERABLES

### 1. Django Model

**File:** `reviews/models.py`

**Model:** `Review`

**Contents:**
- Core identity fields (id, created_at)
- Author context (user ForeignKey, immutable)
- Subject reference (pandit ForeignKey, reference only)
- Review content (rating, review_text, immutable)
- Visibility state (visibility_state, mutable by governance only)
- System metadata (created_source, last_visibility_change_at)
- Database constraints (unique_user_pandit_review)
- Indexes for efficient querying
- clean() method for Django admin/forms only (not runtime enforcement)

### 2. Policy Document

**File:** `REVIEW_MODEL_DEFINITION.md`

**Contents:**
- Minimal data contract definition
- Explicitly forbidden fields (trust score, ranking weight, booking/payment reference, etc.)
- Data principles (minimal by design, immutable content, visibility-only mutation, isolation)
- Model schema summary
- Database constraints and indexes
- Module boundary alignment
- Validation checklist

---

## 🎯 KEY ARCHITECTURAL DECISIONS

### 1. Minimal Schema Design

**Decision:** Only essential fields required to store a review. No derived fields, no computed values, no cross-module dependencies.

**Rationale:** Minimal schema prevents architectural contamination and ensures reviews remain isolated from operational systems.

**Impact:** Clean separation of concerns, no unintended dependencies, safe for future extensions.

---

### 2. Immutable Content Fields

**Decision:** `rating` and `review_text` are immutable once submitted. No editing, no deletion, no modification.

**Rationale:** Reviews represent user voice at a point in time. Immutability preserves authenticity and prevents tampering.

**Impact:** Reviews are permanent records of user opinion, ensuring accountability and historical accuracy.

---

### 3. Visibility State (Mutable by Governance Only)

**Decision:** `visibility_state` can change (visible → under_review → hidden), but only by governance. Changes are tracked via `last_visibility_change_at`.

**Rationale:** Visibility control is a moderation function, not a user or pandit right. Governance makes manual, traceable decisions.

**Impact:** Clear moderation authority, traceable governance actions, no unauthorized visibility changes.

---

### 4. Unique Constraint (Conceptual)

**Decision:** Database-level unique constraint on `(user, pandit)` prevents duplicate reviews, but business logic enforcement (e.g., one review per interaction) is handled at service layer.

**Rationale:** Database constraint provides data integrity, but business rules (e.g., review eligibility) belong in service layer.

**Impact:** Data integrity at DB level, business logic at service level, clear separation of concerns.

---

### 5. No Forbidden Fields

**Decision:** Explicitly excluded fields: trust score, ranking weight, booking/payment reference, moderation notes, abuse flags, aggregated rating cache, SEO metadata.

**Rationale:** These fields would create dependencies on other modules or imply behaviors that reviews must not have.

**Impact:** Reviews remain isolated, no cross-module contamination, no unintended behaviors.

---

## 🔒 HARD BOUNDARIES ESTABLISHED

### Forbidden Fields

1. ❌ Trust score (no trust linkage)
2. ❌ Search ranking weight (no ranking impact)
3. ❌ Booking reference (no booking linkage)
4. ❌ Payment reference (no payment linkage)
5. ❌ Pandit response field (no public responses)
6. ❌ Moderation notes (moderation is separate)
7. ❌ Abuse flags (abuse handling is separate)
8. ❌ Aggregated rating cache (aggregation is separate)
9. ❌ SEO metadata (SEO is separate)

---

## 🔗 MODULE ALIGNMENT

### Dependencies

- **Module 1 — User & Roles:** User reference (author and subject)
- **Module 4 — Pandit Profile:** Reviews displayed on profile (visible only)
- **Module 5 — Dashboards:** Read-only display for Pandits
- **Module 8 — Booking Intent:** Reviews are post-interaction (no linkage)
- **Module 11 — Governance:** Governance controls visibility only

### Isolation

- **Module 7 — Search:** ❌ No search ranking linkage
- **Module 3 — Trust Chain:** ❌ No trust score linkage
- **Module 8 — Booking Intent:** ❌ No booking reference

---

## ✅ VALIDATION CHECKLIST (ALL PASSED)

✅ No booking/payment fields  
✅ No trust or ranking data  
✅ Review content immutable (rating, review_text)  
✅ Visibility state only, no logic  
✅ No aggregation fields  
✅ No moderation fields  
✅ No SEO fields  
✅ No derived or computed fields  
✅ Minimal schema (only essential fields)  
✅ Isolation from other modules  
✅ clean() method for admin/forms only (not runtime enforcement)  
✅ No save() override (enforcement at service layer)  

---

## 📊 TASK METRICS

- **Django Model:** 1 model created (`Review`)
- **Model Fields:** 9 fields (id, created_at, user, pandit, rating, review_text, visibility_state, created_source, last_visibility_change_at)
- **Database Constraints:** 1 unique constraint (unique_user_pandit_review)
- **Indexes:** 4 indexes for efficient querying
- **Forbidden Fields:** 9 categories explicitly excluded
- **Policy Document:** 1 file created

---

## 🎉 TASK STATUS

**Task 9.4 — Review Model Definition**  
**Status:** ✅ **COMPLETE & LOCKED**

The Review model is defined following "MODELS ONLY" principles, with minimal schema, immutable content, and clear isolation from other modules.

---

## ⏭️ NEXT TASK

**Task 9.5** — Submit Review (BACKEND ONLY)

This task will define:
- Review submission flow (authentication, explicit action, passive validation, persistence)
- Disallowed behaviors at submission (no ranking impact, no trust impact, no notifications)
- Submission principles (write-once, non-authoritative, backend-only, side-effect free)

---

## 📝 NOTES

- Model follows "MODELS ONLY" principle (no business logic, no enforcement)
- Content fields (rating, review_text) are immutable
- Visibility state is mutable by governance only
- Unique constraint prevents duplicate reviews at DB level
- Business logic enforcement (e.g., review eligibility) is deferred to service layer (Task 9.5)
- clean() method is for Django admin/forms only, not runtime enforcement
- No save() override; enforcement happens at service layer






