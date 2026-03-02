# Module 9 — Ratings & Reviews (Post-Interaction) — All Tasks Summary

**Module:** 9 — Ratings & Reviews  
**Total Tasks:** 15  
**Status:** All tasks defined and ready for implementation

---

## 📋 Module 9 Overview

**Purpose:** Add feedback loop after interaction.

**Includes:**
- Review eligibility rules
- One review per interaction
- Rating aggregation
- Abuse prevention
- Moderation hooks

**Dependencies:**
- ✔ Module 8 (Booking Intent)
- ✔ Module 4 (Pandit Profile)

**Architectural Rule:** Reviews require context, not anonymous input. Reviews inform users — they do not drive the system.

---

## 🔹 Task 9.1 — Ratings & Reviews Strategy & Scope Boundaries (NO CODE)

**Task Type:** Architecture & Policy  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define what Ratings & Reviews ARE and what they must NEVER become.

**Key Points:**
- Reviews are user-submitted feedback artifacts, post-interaction expressions, opinion-based and subjective
- Reviews are NOT verification mechanisms, trust signals, ranking inputs, booking validators, SEO levers, or transaction evidence
- Must NEVER: affect search ordering, modify trust chains, influence recommendation logic, change pandit visibility, trigger penalties automatically

---

## 🔹 Task 9.2 — Review Visibility & Access Rules (NO CODE)

**Task Type:** Architecture & Policy  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define WHO CAN SEE WHAT — not who can act.

**Visibility Rules:**
- **Guests:** ❌ Cannot view reviews or ratings (login-gated)
- **Logged-in Users:** ✅ Can view published reviews and aggregate rating display (non-ranking)
- **Review Authors:** ✅ Can view own submitted reviews and status labels
- **Pandits:** ✅ Can view reviews written about them (observe only)
- **Admin/Governance:** ✅ Full review visibility (silent, read-only)

---

## 🔹 Task 9.3 — Review Data Ownership & Lifecycle (NO CODE)

**Task Type:** Architecture & Policy  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define WHO OWNS REVIEWS and HOW THEY LIVE & DIE.

**Ownership:**
- **Review Author (User):** Owns the expression, identity tied permanently, cannot edit/delete after submission
- **Platform:** Stores review, maintains lifecycle states, enforces immutability
- **Pandit:** Subject of review only, no ownership or control
- **Governance:** Moderation & visibility control only

**Lifecycle:** Created once, immutable content, may change visibility state (Visible / Under Review / Hidden), eventually archived

---

## 🔹 Task 9.4 — Review Model Definition (MODELS ONLY)

**Task Type:** Data Architecture  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define the minimum, safe data contract required to store a user review.

**Core Fields:**
- Identity: review_id, created_at
- Author Context: user_id (logged-in user, no anonymous reviews)
- Subject Reference: pandit_id (reference only)
- Review Content: rating, review_text (immutable)
- Visibility State: visibility_state (visible / under_review / hidden)
- System Metadata: created_source, last_visibility_change_at

**Forbidden Fields:** Trust score, search ranking weight, booking/payment reference, pandit response, moderation notes, abuse flags, aggregated rating cache, SEO metadata

---

## 🔹 Task 9.5 — Submit Review (BACKEND ONLY)

**Task Type:** Architecture & Policy (Backend Scope Only)  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define HOW A REVIEW IS CREATED — NOTHING AFTER.

**Submission Flow:**
1. Authentication Check (logged-in users only)
2. Explicit User Action (no auto-generation)
3. Passive Validation (structural only, no truthfulness checks)
4. Record Persistence (immutable record, no side-effects)

**Disallowed:** Affect search ranking, affect trust score, trigger notifications, trigger moderation actions, link to booking/payment

---

## 🔹 Task 9.6 — Review Display Rules (NO CODE)

**Task Type:** Architecture & Policy  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define HOW REVIEWS MAY BE DISPLAYED — NOT HOW THEY ARE GENERATED OR USED.

**Display Rules:**
- **Display Scope:** On Pandit public profile pages, in dedicated reviews sections only. NOT inside search result cards, as ranking signals, or as badges
- **Ordering:** By recency (newest first) or neutral pagination. NOT by rating value, sentiment, engagement, or helpfulness votes
- **Aggregated Rating:** Display-only, does not influence ranking, trust, or eligibility
- **Visibility State:** Only visible reviews shown, hidden reviews fully invisible

---

## 🔹 Task 9.7 — Pandit Review Reporting Rules (NO CODE)

**Task Type:** Architecture & Policy  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define HOW PANDITS MAY REPORT REVIEWS — NOT HOW REVIEWS ARE REMOVED.

**Reporting Rules:**
- **Who Can Report:** Only the reviewed Pandit
- **What Can Be Reported:** Abusive language, harassment, hate/explicit content, clearly irrelevant/spam content
- **Reporting Action:** Review remains visible, flagged for governance review only
- **Pandit Limitations:** Cannot hide/edit reviews, cannot respond with moderation authority, cannot see governance outcomes

---

## 🔹 Task 9.8 — Review Moderation & Governance Contract (NO CODE)

**Task Type:** Architecture & Policy (Governance Contract Only)  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define WHO moderates reviews and under what authority.

**Governance Roles:**
- **Admin/Super Admin:** May review reported reviews, change visibility state, apply moderation decisions manually. Must NOT edit content, rewrite opinions, affect search/trust
- **System:** Routes reported reviews to governance, maintains moderation state. No automatic moderation, no NLP judgment, no auto-removal
- **Pandits & Users:** ❌ No moderation authority

**Allowed Actions:** Mark as under_review, change to hidden, restore to visible (all manual and traceable)

---

## 🔹 Task 9.9 — Review Status States & Transitions (NO CODE)

**Task Type:** Architecture & Policy (State Semantics Only)  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define DESCRIPTIVE STATES ONLY (visibility, not correctness).

**Allowed States:**
- **Visible:** Review is publicly visible, default state after submission
- **Under Review:** Review flagged for governance review, still visible (unless explicitly hidden)
- **Hidden:** Review not publicly visible, content preserved internally

**Allowed Transitions:** Visible → Under Review, Under Review → Hidden, Hidden → Visible, Under Review → Visible (no irreversible transitions)

---

## 🔹 Task 9.10 — Ratings Aggregation Rules (NO CODE)

**Task Type:** Architecture & Policy (Aggregation Semantics Only)  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define HOW ratings are aggregated — not how they are used.

**Aggregation Rules:**
- **May:** Compute simple arithmetic average, display total number of ratings, display rating distribution
- **Must:** Be deterministic, based only on visible reviews, ignore hidden reviews
- **Must NOT:** Weight by recency/user status, adjust algorithmically, predict quality, influence search/trust/booking

**Isolation Guarantees:** No impact on Search, Trust Chains, Booking/Availability, Governance, SEO

---

## 🔹 Task 9.11 — Reviews × Trust & SEO Boundaries (NO CODE)

**Task Type:** Architecture & Policy (Boundary & Isolation Contract)  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define WHAT REVIEWS MUST NEVER INFLUENCE.

**Trust Boundaries:**
- Reviews must NEVER: increase trust chain strength, grant verified/certified status, influence trust eligibility, modify referral credibility

**SEO Boundaries:**
- Reviews must NEVER: be indexed as authoritative SEO content, generate SEO titles/descriptions, influence canonical URLs, be used for keyword targeting, be summarized into SEO copy

**Forbidden Cross-Module Use:** Search ranking logic, recommendation engines, trust/verification systems, governance scoring models, availability prioritization

---

## 🔹 Task 9.12 — Review Abuse Prevention & Rate Limits (NO CODE)

**Task Type:** Architecture & Policy (Preventive Controls — Conceptual Only)  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define INFRASTRUCTURE PROTECTION ONLY.

**Abuse Types (Descriptive):** Excessive submissions, repeated reviews, automated posting, copy-paste content, coordinated flooding

**Allowed Preventive Measures:** Rate-limiting, throttling, temporary suppression (infrastructure-level, user-agnostic, non-punitive, non-persistent)

**Forbidden:** Penalize users/Pandits, affect review visibility permanently, affect search ranking, affect trust/verification, trigger governance automatically

---

## 🔹 Task 9.13 — Review Audit & Traceability Rules (NO CODE)

**Task Type:** Architecture & Policy (Governance Visibility Only)  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define TRACEABILITY — NOT ENFORCEMENT.

**Audit Scope:** Review creation timestamp, review ID and Pandit reference, reviewer ID (internal only), status transitions, governance action timestamps

**Forbidden Audit Data:** Behavioral analysis, reviewer intent assumptions, trust/abuse labels, automated conclusions, internal ranking signals, availability/booking data

**Access Rules:** Governance/Admin only, read-only, no Pandit/User access

---

## 🔹 Task 9.14 — Review UX Signals & Disclaimers (NO CODE)

**Task Type:** Architecture & Policy (UX Semantics & Expectation Safety)  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define WHAT must be communicated to users — not HOW it is designed.

**Required UX Signals:**
1. Opinion-Based Signal (reviews reflect personal opinions, subjective experiences, not factual guarantees)
2. No Guarantee Signal (reviews do not guarantee service quality, past experience does not ensure future results)
3. Non-Authoritative Signal (reviews do not decide eligibility, control bookings, or enforce trust)
4. Moderation Awareness Signal (reviews may be moderated, moderation does not imply falsehood)
5. Logged-in Visibility Signal (reviews visible only to logged-in users)

**Forbidden Implications:** Guaranteed quality, platform endorsement, verified outcomes, priority treatment, trust certification, ranking advantage

---

## 🔹 Task 9.15 — Review × Future Recommendation Compatibility (NO CODE)

**Task Type:** Architecture & Policy (Forward-Compatibility Contract)  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define FUTURE COMPATIBILITY — NOT FUTURE LOGIC.

**Compatibility Guarantees:**
- Schema Stability: Existing review fields remain valid
- Meaning Stability: Ratings remain subjective, reviews remain opinion-based
- Isolation: Recommendation systems may read, must never mutate reviews or change historical meaning

**Non-Guarantees:** Reviews will affect recommendations, influence ranking, produce trust scores, become eligibility gates

**Extension Principles:** Future systems may read review text/ratings and reference IDs, but must never rewrite historical reviews, re-score old ratings, or affect search ordering via reviews

---

## 🎉 MODULE 9 COMPLETE

**All 15 tasks (9.1-9.15) are now COMPLETE & LOCKED**

Module 9 — Ratings & Reviews is fully documented and ready for implementation.

---

## 📊 Task Summary Table

| Task | Title | Type | Status |
|------|-------|------|--------|
| 9.1 | Ratings & Reviews Strategy & Scope Boundaries | NO CODE | 🔒 LOCKED |
| 9.2 | Review Visibility & Access Rules | NO CODE | 🔒 LOCKED |
| 9.3 | Review Data Ownership & Lifecycle | NO CODE | 🔒 LOCKED |
| 9.4 | Review Model Definition | MODELS ONLY | 🔒 LOCKED |
| 9.5 | Submit Review | BACKEND ONLY | 🔒 LOCKED |
| 9.6 | Review Display Rules | NO CODE | 🔒 LOCKED |
| 9.7 | Pandit Review Reporting Rules | NO CODE | 🔒 LOCKED |
| 9.8 | Review Moderation & Governance Contract | NO CODE | 🔒 LOCKED |
| 9.9 | Review Status States & Transitions | NO CODE | 🔒 LOCKED |
| 9.10 | Ratings Aggregation Rules | NO CODE | 🔒 LOCKED |
| 9.11 | Reviews × Trust & SEO Boundaries | NO CODE | 🔒 LOCKED |
| 9.12 | Review Abuse Prevention & Rate Limits | NO CODE | 🔒 LOCKED |
| 9.13 | Review Audit & Traceability Rules | NO CODE | 🔒 LOCKED |
| 9.14 | Review UX Signals & Disclaimers | NO CODE | 🔒 LOCKED |
| 9.15 | Review × Future Recommendation Compatibility | NO CODE | 🔒 LOCKED |

---

## ⏭️ Next Module

**Module 10** — Public Trust Display

This module will define:
- "Referred by" display
- Experience badges
- Average rating
- Review count
- Availability confidence






