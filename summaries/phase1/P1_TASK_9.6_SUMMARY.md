# Task 9.6 — Review Display Rules — Summary

**Module:** 9 — Ratings & Reviews  
**Task Type:** Architecture & Policy (NO CODE)  
**Status:** ✅ COMPLETE & LOCKED  
**Completion Date:** [Current Date]

---

## 📋 TASK OVERVIEW

**Task 9.6** defines **HOW REVIEWS MAY BE DISPLAYED**, ensuring reviews are informational only and do not influence search, trust, booking, or other operational systems.

**Core Principle:** Display ≠ decision-making. Reviews inform users, not drive system behavior.

---

## ✅ DELIVERABLES

### 1. Policy Document

**File:** `REVIEW_DISPLAY_RULES.md`

**Contents:**
- Display scope (where reviews may be shown, where they must not be shown)
- Ordering rules (recency, neutral pagination - NOT by rating or sentiment)
- Aggregated rating display (display-only, non-ranking, non-trust)
- Visibility state handling (only visible reviews shown, hidden reviews fully invisible)
- Review content display (what may be shown, what must not be shown)
- Review count display (informational only, not a metric)
- Explicitly forbidden display behaviors (8 categories)
- Display principles (Informational Only, Neutral Presentation, Isolation, Transparency)
- Module boundary alignment
- Validation checklist

---

## 🎯 KEY ARCHITECTURAL DECISIONS

### 1. Display Scope (Profile Pages Only)

**Decision:** Reviews may be displayed on Pandit public profile pages and in dedicated reviews sections only. Reviews must NOT appear in search results, as ranking signals, or as badges.

**Rationale:** Reviews are informational only. Including them in search results would create ranking influence, violating the non-authoritative principle.

**Impact:** Reviews remain isolated from search and discovery, ensuring search neutrality.

---

### 2. Neutral Ordering (Recency Only)

**Decision:** Reviews may be ordered by recency (newest first) or neutral pagination. Reviews must NOT be ordered by rating value, sentiment, engagement, or helpfulness votes.

**Rationale:** Neutral ordering prevents implicit prioritization and ensures all visible reviews are treated equally.

**Impact:** No bias in review display, no manipulation of review visibility based on content.

---

### 3. Aggregated Rating (Display-Only)

**Decision:** Aggregated rating may be shown as a static summary (display-only). Aggregation does not influence ranking, trust, or eligibility.

**Rationale:** Aggregated ratings are informational summaries, not authoritative scores. They help users understand overall sentiment without driving system behavior.

**Impact:** Users can see average ratings without reviews affecting search, trust, or booking outcomes.

---

### 4. Visibility State Handling (Hidden = Invisible)

**Decision:** Only visible reviews are shown publicly. Under_review and hidden reviews are not shown, with no placeholders or count leakage.

**Rationale:** Hidden reviews are governance-controlled. Public display should not reveal moderation actions or hidden content.

**Impact:** Clean public display, no governance metadata leakage, no confusion about review visibility.

---

### 5. No Competitive Comparison

**Decision:** Reviews must not be used for competitive comparison, side-by-side displays, or "better than" indicators.

**Rationale:** Reviews are opinions, not competitive metrics. Comparison would imply ranking or evaluation authority.

**Impact:** Reviews remain informational, not competitive, ensuring fair representation of all Pandits.

---

## 🔒 HARD BOUNDARIES ESTABLISHED

### Forbidden Display Behaviors

1. ❌ Affect search ordering (no review-based ranking)
2. ❌ Influence trust chains (no trust score calculation)
3. ❌ Gate booking intent (no booking eligibility based on reviews)
4. ❌ Show moderation reasoning (no public disclosure of moderation actions)
5. ❌ Expose governance actions (no report history or moderation workflow visibility)
6. ❌ Compare Pandits competitively (no side-by-side comparisons)
7. ❌ Personalize or recommend (no user-specific ordering or filtering)
8. ❌ Create persuasive framing (no emphasis on high/low ratings)

---

## 🔗 MODULE ALIGNMENT

### Dependencies

- **Module 4 — Pandit Profile:** Reviews displayed on profile pages (visible only)
- **Module 5 — Dashboards:** Read-only display for Pandits

### Isolation

- **Module 7 — Search:** ❌ No reviews in search results
- **Module 8 — Booking Intent:** ❌ No reviews in booking intent
- **Module 11 — Governance:** ❌ No governance metadata in public display

---

## ✅ VALIDATION CHECKLIST (ALL PASSED)

✅ Reviews shown only on profile pages (not in search results)  
✅ No ranking or trust impact from display  
✅ Neutral ordering only (recency, not rating or sentiment)  
✅ Hidden reviews fully invisible (no placeholders or leakage)  
✅ No governance leakage (no moderation metadata in display)  
✅ Aggregated rating is display-only (no ranking or trust influence)  
✅ Review count is informational only (not a metric)  
✅ No competitive comparison (no side-by-side displays)  
✅ No personalization (no user-specific ordering)  
✅ No persuasive framing (no emphasis on high/low ratings)  

---

## 📊 TASK METRICS

- **Policy Document:** 1 file created
- **Display Rules:** 6 categories defined (Display Scope, Ordering, Aggregation, Visibility, Content, Count)
- **Forbidden Behaviors:** 8 categories explicitly disallowed
- **Display Principles:** 4 principles established (Informational Only, Neutral Presentation, Isolation, Transparency)
- **Module Alignments:** 5 module relationships defined

---

## 🎉 TASK STATUS

**Task 9.6 — Review Display Rules**  
**Status:** ✅ **COMPLETE & LOCKED**

Review display rules are defined with clear boundaries, ensuring reviews are informational only and do not influence operational systems.

---

## ⏭️ NEXT TASK

**Task 9.7** — Pandit Review Reporting Rules (NO CODE)

This task will define:
- Who can report reviews (only reviewed Pandit)
- What can be reported (abusive language, harassment, hate/explicit content, spam)
- Reporting action semantics (review remains visible, flagged for governance)
- Pandit limitations (cannot hide/edit/delete reviews, cannot see governance outcomes)

---

## 📝 NOTES

- Reviews are displayed on Pandit profile pages only, not in search results
- Ordering is neutral (recency only), not by rating or sentiment
- Aggregated ratings are display-only, not used for ranking or trust
- Hidden reviews are fully invisible, no placeholders or leakage
- No competitive comparison or persuasive framing
- Reviews remain isolated from operational systems






