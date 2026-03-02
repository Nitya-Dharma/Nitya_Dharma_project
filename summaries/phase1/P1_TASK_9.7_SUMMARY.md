# Task 9.7 — Pandit Review Reporting Rules — Summary

**Module:** 9 — Ratings & Reviews  
**Task Type:** Architecture & Policy (NO CODE)  
**Status:** ✅ COMPLETE & LOCKED  
**Completion Date:** [Current Date]

---

## 📋 TASK OVERVIEW

**Task 9.7** defines **HOW PANDITS MAY REPORT REVIEWS**, providing a safe, non-authoritative channel to flag problematic content without giving Pandits control over review visibility or moderation.

**Core Principle:** Reporting ≠ enforcement. Pandits can report, but governance makes all decisions.

---

## ✅ DELIVERABLES

### 1. Policy Document

**File:** `PANDIT_REVIEW_REPORTING_RULES.md`

**Contents:**
- Who can report (only reviewed Pandit, logged-in only)
- What can be reported (abusive language, harassment, hate/explicit content, spam)
- Reporting action semantics (review remains visible, flagged for governance only)
- Pandit limitations (cannot hide/edit/delete, cannot see governance outcomes)
- Forbidden reporting behaviors (7 categories)
- Reporting principles (Non-Authoritative, Non-Retaliatory, Governance-Dependent, Transparency)
- Module boundary alignment
- Validation checklist

---

## 🎯 KEY ARCHITECTURAL DECISIONS

### 1. Reporting Authority (Pandit Only)

**Decision:** Only the reviewed Pandit can report reviews about themselves. No third-party reporting via Pandit tools.

**Rationale:** Pandits are the subjects of reviews and have the most direct knowledge of whether a review is problematic. Limiting reporting to the reviewed Pandit prevents abuse and ensures reports are relevant.

**Impact:** Clear reporting authority, prevents third-party abuse, ensures relevance of reports.

---

### 2. Reportable Content (Abuse, Not Disagreement)

**Decision:** Pandits may report reviews for abusive language, harassment, hate/explicit content, or spam. Pandits must NOT report reviews for disagreement, negative feedback, or low ratings.

**Rationale:** Reporting is for content violations, not opinion disputes. Negative feedback and low ratings are legitimate expressions of user experience.

**Impact:** Prevents misuse of reporting system, protects user voice, ensures reports are for genuine violations.

---

### 3. Reporting Does Not Change Visibility

**Decision:** When a review is reported, it remains visible. No automatic hiding, no immediate action, no visibility changes. Review is flagged for governance review only.

**Rationale:** Reporting is a signal, not an enforcement mechanism. Only governance can change visibility state. Auto-hiding would give Pandits de facto moderation power.

**Impact:** Reviews remain visible until governance decides, prevents Pandit control, ensures due process.

---

### 4. Pandit Limitations (No Self-Moderation)

**Decision:** Pandits cannot hide, edit, delete, or respond with moderation authority. Pandits cannot see governance outcomes, moderation notes, or reviewer identity.

**Rationale:** Pandits are subjects of reviews, not moderators. Giving Pandits moderation power would create conflicts of interest and undermine review integrity.

**Impact:** Clear separation of concerns, prevents conflicts of interest, maintains review integrity.

---

### 5. Non-Retaliatory Reporting

**Decision:** Reporting must not trigger penalties, restrictions, or negative consequences for reviewers. Reporting is a channel to governance, not a weapon.

**Rationale:** Reporting should be a safe mechanism for flagging problematic content, not a tool for retaliation against reviewers.

**Impact:** Protects reviewer safety, encourages legitimate reporting, prevents abuse of reporting system.

---

## 🔒 HARD BOUNDARIES ESTABLISHED

### Forbidden Reporting Behaviors

1. ❌ Auto-hide reviews (no automatic hiding after report)
2. ❌ Affect rating aggregation (no exclusion from calculations)
3. ❌ Affect trust or ranking (no search or trust impact)
4. ❌ Trigger penalties (no negative consequences for reviewer)
5. ❌ Notify users automatically (no automatic notifications)
6. ❌ Create retaliation mechanisms (no negative consequences for reviewer)
7. ❌ Enable self-moderation (no Pandit control over visibility)

---

## 🔗 MODULE ALIGNMENT

### Dependencies

- **Module 1 — User & Roles:** Pandit must be logged in to report
- **Module 4 — Pandit Profile:** Reports are about reviews on Pandit profile
- **Module 5 — Dashboards:** Pandits can see reports they made (status only)
- **Module 11 — Governance:** Reports are routed to governance for review

### Isolation

- **Module 7 — Search:** ❌ No search impact from reports
- **Module 3 — Trust Chain:** ❌ No trust impact from reports
- **Module 8 — Booking Intent:** ❌ No booking impact from reports

---

## ✅ VALIDATION CHECKLIST (ALL PASSED)

✅ Pandit can report but not act (no self-moderation)  
✅ Review remains visible after report (no auto-hiding)  
✅ No trust/search impact (no ranking or trust changes)  
✅ No auto-removal (no automatic hiding or deletion)  
✅ Governance-only resolution (admins make all decisions)  
✅ No retaliation (no negative consequences for reviewer)  
✅ Reporting is non-authoritative (signals concern only)  
✅ Pandits cannot see governance outcomes (no moderation visibility)  

---

## 📊 TASK METRICS

- **Policy Document:** 1 file created
- **Reporting Rules:** 4 categories defined (Who Can Report, What Can Be Reported, Reporting Action Semantics, Pandit Limitations)
- **Forbidden Behaviors:** 7 categories explicitly disallowed
- **Reporting Principles:** 4 principles established (Non-Authoritative, Non-Retaliatory, Governance-Dependent, Transparency)
- **Module Alignments:** 4 module relationships defined

---

## 🎉 TASK STATUS

**Task 9.7 — Pandit Review Reporting Rules**  
**Status:** ✅ **COMPLETE & LOCKED**

Pandit review reporting rules are defined with clear boundaries, ensuring reporting is a safe, non-authoritative channel to governance without giving Pandits control over reviews.

---

## ⏭️ NEXT TASK

**Task 9.8** — Review Moderation & Governance Contract (NO CODE)

This task will define:
- Who moderates reviews (Admin/Super Admin only)
- System role (routes reports, maintains state, no auto-moderation)
- Allowed moderation actions (change visibility state, manual decisions)
- Forbidden moderation actions (edit content, rewrite opinions, affect search/trust)

---

## 📝 NOTES

- Reporting is a channel to governance, not a control mechanism
- Reviews remain visible after reporting until governance decides
- Pandits cannot self-moderate or see governance outcomes
- Reporting is non-retaliatory and non-authoritative
- Only governance can change review visibility state
- Reporting does not affect search, trust, ranking, or aggregation






