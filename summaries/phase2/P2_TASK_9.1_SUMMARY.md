# Task 9.1 — Ratings & Reviews Strategy & Scope Boundaries (NO CODE)

**Module:** 9 — Ratings & Reviews (Phase 2)  
**Task Type:** Architecture & Policy (NO CODE)  
**Status:** ✅ COMPLETE & LOCKED

---

## ⚠️ CRITICAL RULE (NON-NEGOTIABLE)

This task defines **WHAT Ratings & Reviews ARE** and what they must **NEVER become**.

❌ NO search ranking influence  
❌ NO trust score calculation  
❌ NO referral eligibility impact  
❌ NO payment linkage  
❌ NO booking validation  
❌ NO pandit self-moderation  
❌ NO auto-approval or auto-removal

**If reviews affect discovery, trust, or transactions → REJECT IMMEDIATELY.**

---

## 🧠 PURPOSE (Senior Architect View)

This task exists to define Ratings & Reviews as **post-interaction, user-expressed feedback only**.

Ratings & Reviews allow users to:
- Share personal experience feedback
- Express opinions after an interaction
- Inform other logged-in users

Ratings & Reviews do NOT:
- Decide pandit quality
- Influence platform ranking
- Act as trust proof
- Trigger moderation automatically
- Replace governance judgment

**Reviews inform users — they do not drive the system.**

---

## 🧩 FORMAL DEFINITION (LOCKED)

### Ratings & Reviews ARE:
- User-submitted feedback artifacts
- Post-interaction expressions
- Opinion-based and subjective
- Visible only to logged-in users
- Independent of booking, trust, or payments
- Social proof only

### Ratings & Reviews ARE NOT:
- Verification mechanisms
- Trust signals
- Ranking inputs
- Booking validators
- SEO levers
- Transaction evidence
- Quality scores
- Recommendation signals

**Feedback ≠ Authority**

---

## 🚫 HARD SCOPE BOUNDARIES (LOCKED)

Ratings & Reviews must **NEVER**:

1. ❌ Affect search ordering (Module 7)
2. ❌ Modify trust chains (Module 3)
3. ❌ Influence recommendation logic (Module 15)
4. ❌ Change pandit visibility (Module 11)
5. ❌ Trigger penalties automatically
6. ❌ Lock or unlock platform features
7. ❌ Affect referral systems (Module 3)
8. ❌ Act as proof of service completion
9. ❌ Calculate trust scores (Module 10)
10. ❌ Drive governance decisions (Module 11)

---

## 🔗 MODULE BOUNDARY ALIGNMENT

| Module | Relationship |
|--------|-------------|
| Module 4 — Pandit Profile | Reviews displayed only (read-only) |
| Module 5 — Dashboards | Read-only display |
| Module 6 — Availability | ❌ No connection |
| Module 7 — Search | ❌ No ranking impact |
| Module 8 — Booking Intent | Post-intent context only (read-only) |
| Module 10 — Trust Display | Display-only consumption (no calculation) |
| Module 11 — Governance | Moderation authority only (human-controlled) |
| Module 15 — Recommendations | ❌ No recommendation signals |

**Module 9 is informational, not operational.**

---

## 🎯 DESIGN PRINCIPLES (LOCKED)

### User-Voice Principle
- Reviews represent user opinion
- Platform does not validate sentiment
- No editorial control over content (except moderation)

### Non-Authoritative Principle
- Reviews carry no enforcement power
- No automated consequences
- No business logic driven by reviews

### Governance-Controlled Principle
- Only admins moderate (Module 11)
- No pandit self-approval or deletion
- Human-controlled moderation only

### Isolation Principle
- Reviews are isolated from trust, ranking, and payments
- No cross-module logic leakage
- Clean boundaries enforced

### Social Proof Only Principle
- Reviews = social proof
- Reviews ≠ trust score
- Reviews ≠ quality metric
- Reviews ≠ verification

---

## 🔒 VISIBILITY RULES (LOCKED)

### Guest Users (Not Logged In)
- ❌ Cannot view reviews
- ❌ Cannot view ratings
- ✅ "Login to view reviews" CTA only

### Logged-in Users
- ✅ Can view published reviews
- ✅ Can view aggregate rating display (non-ranking)
- ❌ Cannot see moderation status
- ❌ Cannot see audit or report history

### Pandits
- ✅ Can view reviews about them
- ✅ Can report reviews (not delete)
- ❌ Cannot respond to reviews
- ❌ Cannot moderate reviews

### Admins
- ✅ Can view all reviews (including hidden/moderated)
- ✅ Can see moderation status
- ✅ Can see audit history
- ✅ Can moderate (Module 11)

---

## ✅ VALIDATION CHECKLIST

Before locking this task, confirm:

- ✅ Reviews do not affect search
- ✅ Reviews do not affect trust
- ✅ Reviews do not affect payments
- ✅ Pandits cannot moderate
- ✅ Governance is manual and isolated
- ✅ Guests cannot view reviews
- ✅ No ML or personalization
- ✅ No paid APIs
- ✅ Backend-only enforcement

**If any fail → STOP.**

---

## 📌 TASK STATUS

**Task 9.1 — Ratings & Reviews Strategy & Scope Boundaries**  
**Type:** Policy & Architecture (NO CODE)  
**Status:** ✅ LOCKED

---

## 📁 FILES CREATED/MODIFIED/DELETED

### ✅ Files Created
- `P2_M9_9.1_RATINGS_REVIEWS_STRATEGY_SCOPE.md` — Policy documentation

### ❌ Files NOT Created
- No Python files
- No Django apps
- No models, views, serializers, or migrations

---

**Task 9.1 Complete — Ready for Task 9.2**

