# Module 8 — Booking Intent (NO PAYMENT) — All Tasks Summary

**Module:** 8 — Booking Intent (Communication Only)  
**Total Tasks:** 14  
**Status:** All tasks defined and ready for implementation

---

## 📋 Module 8 Overview

**Purpose:** Allow users to express intent without money.

**Includes:**
- Request form
- Pandit receives notification
- Accept / reject flow
- Status lifecycle

**Dependencies:**
- ✔ Module 6 (Availability & Calendar)
- ✔ Module 7 (User Search & Discovery)

**Architectural Rule:** Booking Intent is a communication-only signal, not a booking or commitment.

---

## 🔹 Task 8.1 — Booking Intent Definition, Purpose & Hard Limits (NO CODE)

**Task Type:** Architecture & Policy  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define what Booking Intent IS and what it must NEVER become.

**Key Points:**
- Booking Intent is a user-generated signal of interest
- Temporary, non-binding request
- Communication artifact, not a contract
- Must NEVER: lock availability, modify schedules, guarantee response, trigger payment

---

## 🔹 Task 8.2 — Booking Intent Ownership, Actors & Lifecycle (NO CODE)

**Task Type:** Architecture & Policy  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define WHO OWNS Booking Intent, WHO CAN SEE IT, and HOW IT LIVES & DIES.

**Actors:**
1. **User (Intent Creator)** — Sole creator, owns the intent record
2. **Pandit (Intent Receiver)** — Passive recipient, read-only visibility
3. **Platform (System Custodian)** — Stores intent safely, maintains lifecycle
4. **Governance (Read-Only Oversight)** — Audit-only visibility

**Lifecycle:** Created → Exists → Expires (temporal, not procedural)

---

## 🔹 Task 8.3 — Booking Intent Minimal Data Model (MODELS ONLY)

**Task Type:** Data Architecture  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define the smallest possible data structure needed to represent Booking Intent.

**Core Fields:**
- Identity: intent_id, created_at, expires_at
- User Context: user_id, user_note (optional)
- Pandit Reference: pandit_id
- Intent Context: requested_pooja, preferred_date/time/location (declarative only)
- System Metadata: visibility_state, created_source

**Forbidden Fields:** Price, payment status, availability lock, confirmation state, acceptance/rejection flags

---

## 🔹 Task 8.4 — Booking Intent Creation Flow (BACKEND ONLY)

**Task Type:** Architecture & Policy (Backend Scope Only)  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define HOW a Booking Intent record may be CREATED — nothing more.

**Creation Steps:**
1. Explicit User Action (mandatory)
2. Minimal Data Capture (references, preferences, optional note)
3. Passive Validation (structural only, no feasibility checks)
4. Record Persistence (no side-effects)

**Disallowed at Creation:** Lock calendar slots, modify availability, trigger booking workflows, trigger payment flows

---

## 🔹 Task 8.5 — Booking Intent Visibility Matrix (User / Pandit / Admin) (NO CODE)

**Task Type:** Architecture & Policy  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define WHO CAN SEE WHAT — not what they can do.

**Visibility Matrix:**
- **User:** Full visibility of own intent, cannot edit or enforce response
- **Pandit:** Read-only view of received intents, cannot accept/reject
- **Admin/Governance:** Read-only audit visibility, no mutation
- **Other Modules:** No access (Search, Availability, Payments, Ranking/Trust)

---

## 🔹 Task 8.6 — Booking Intent ↔ Availability Interpretation Rules (NO CODE)

**Task Type:** Architecture & Policy  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define how Booking Intent may reference availability without changing it.

**Rules:**
- Declarative Reference Only (preferences, not constraints)
- No Availability Enforcement (no checks, validation, or blocking)
- Independence Guarantee (multiple intents may coexist for same Pandit/date/time)

**Forbidden:** Check availability, validate feasibility, block other users, reserve slots

---

## 🔹 Task 8.7 — Booking Intent State Machine (Conceptual Only) (NO CODE)

**Task Type:** Architecture & Policy  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define ALLOWED STATES AND TRANSITIONS ONLY.

**Allowed States:**
1. **Pending** — Intent created, no response implied
2. **Viewed** — Pandit has seen intent, no acceptance/rejection implied
3. **Expired** — Intent passed relevance window, automatic and neutral
4. **Closed** — Intent lifecycle ended, outcome outside this module

**Forbidden States:** Accepted, Rejected, Confirmed, Scheduled, Paid, Cancelled

---

## 🔹 Task 8.8 — Booking Intent Notification Events (Contract Only) (NO CODE)

**Task Type:** Architecture & Policy (Event Contract Only)  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define WHEN notifications MAY be emitted — not HOW they are sent.

**Allowed Notification Events:**
1. Booking Intent Created (to Pandit — informational)
2. Booking Intent Viewed (to User — optional)
3. Booking Intent Expired (to User — informational)
4. Booking Intent Closed (to User/Pandit — optional)

**Forbidden Events:** Acceptance, Rejection, Confirmation, Scheduling, Payment, Availability locking

---

## 🔹 Task 8.9 — Booking Intent Expiry, Timeout & Auto-Closure Semantics (NO CODE)

**Task Type:** Architecture & Policy  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define LIFETIME SEMANTICS ONLY (when does intent stop being relevant).

**Concepts:**
- Intent Relevance Window (finite, pre-defined, automatic expiry)
- Expiry Semantics (transitions to Expired, no action required, no outcome inferred)
- Auto-Closure Semantics (may close when relevance window passed or external outcomes occurred)

**Forbidden:** Penalize user/Pandit, affect trust/ranking, affect search results, trigger governance action

---

## 🔹 Task 8.10 — Booking Intent Abuse & Rate-Limiting Policy (NO CODE)

**Task Type:** Architecture & Policy (Preventive Controls — Conceptual Only)  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define ABUSE PREVENTION PRINCIPLES ONLY.

**Abuse Types (Descriptive):** Excessive creation, repeated identical intents, automated generation

**Allowed Preventive Measures:** Rate-limiting, throttling, temporary suppression (infrastructure-level, user-agnostic, non-punitive)

**Forbidden:** Penalize Pandits, affect Search visibility, affect ranking, modify trust status, trigger governance automatically

---

## 🔹 Task 8.11 — Booking Intent Audit & Traceability (Governance Only) (NO CODE)

**Task Type:** Architecture & Policy (Governance Visibility Only)  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define AUDIT VISIBILITY ONLY (for traceability, not enforcement).

**Audit Scope:** Creation timestamp, actor type, referenced Pandit, lifecycle transitions, non-sensitive metadata

**Forbidden Audit Data:** Message contents, personal communications, internal availability data, trust/abuse labels

**Access Rules:** Governance only, read-only, no user/Pandit exposure

---

## 🔹 Task 8.12 — Booking Intent Governance Interactions (Blocking / Reporting) (NO CODE)

**Task Type:** Architecture & Policy (Governance Interaction Semantics Only)  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define HOW GOVERNANCE MAY AFFECT VISIBILITY — NOT EXISTENCE.

**Allowed Governance Actions:**
1. Restrict Visibility (hide from Pandit/user view, maintain internal visibility)
2. Flag for Review (internal only, no user-facing indicators)
3. Freeze Interaction (non-destructive, prevent further interaction)

**Forbidden:** Delete records, alter content, modify availability, affect search ordering, affect trust/reputation, auto-ban users/Pandits

---

## 🔹 Task 8.13 — Booking Intent Forward-Compatibility Contract (NO CODE)

**Task Type:** Architecture & Policy (Future-Proofing Contract)  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define FUTURE COMPATIBILITY — NOT FUTURE FEATURES.

**Guarantees:** Schema stability, state stability, behavioral stability (intent remains non-binding), isolation (new modules may read, not mutate)

**Non-Guarantees:** Automatic upgrade to booking, payment integration, acceptance workflows, scheduling enforcement, pricing logic

---

## 🔹 Task 8.14 — Booking Intent UX Signals & Legal Disclaimers (Conceptual Only) (NO CODE)

**Task Type:** Architecture & Policy (UX & Legal Semantics — Conceptual Only)  
**Status:** 🔒 READY TO LOCK

**Purpose:** Define WHAT must be communicated to users — not HOW it is designed.

**Required UX Signals:**
1. Non-Binding Signal (not a booking, no service confirmed, no obligation)
2. Availability Disclaimer (indicative only, not locked/reserved, may change)
3. No Payment / No Commitment Signal (no payment, no pricing agreed, no contract)
4. Response Expectation Disclaimer (Pandit response optional, no guaranteed response time)
5. Expiry Awareness Signal (time-bound, may expire automatically, expiry is neutral)

**Forbidden Implications:** Booking confirmation, guaranteed acceptance, reserved time slots, payment readiness, priority handling

---

## 🎉 MODULE 8 COMPLETE

**Final Module 8 Status:**
- ✅ Tasks 8.1 → 8.14 COMPLETE & LOCKED
- ✅ No payment
- ✅ No booking
- ✅ No availability locking
- ✅ Communication-only signal
- ✅ All architectural boundaries preserved

---

## 📊 Task Summary Table

| Task | Title | Type | Status |
|------|-------|------|--------|
| 8.1 | Booking Intent Definition, Purpose & Hard Limits | NO CODE | 🔒 LOCKED |
| 8.2 | Booking Intent Ownership, Actors & Lifecycle | NO CODE | 🔒 LOCKED |
| 8.3 | Booking Intent Minimal Data Model | MODELS ONLY | 🔒 LOCKED |
| 8.4 | Booking Intent Creation Flow | BACKEND ONLY | 🔒 LOCKED |
| 8.5 | Booking Intent Visibility Matrix | NO CODE | 🔒 LOCKED |
| 8.6 | Booking Intent ↔ Availability Interpretation Rules | NO CODE | 🔒 LOCKED |
| 8.7 | Booking Intent State Machine | NO CODE | 🔒 LOCKED |
| 8.8 | Booking Intent Notification Events | NO CODE | 🔒 LOCKED |
| 8.9 | Booking Intent Expiry, Timeout & Auto-Closure | NO CODE | 🔒 LOCKED |
| 8.10 | Booking Intent Abuse & Rate-Limiting Policy | NO CODE | 🔒 LOCKED |
| 8.11 | Booking Intent Audit & Traceability | NO CODE | 🔒 LOCKED |
| 8.12 | Booking Intent Governance Interactions | NO CODE | 🔒 LOCKED |
| 8.13 | Booking Intent Forward-Compatibility Contract | NO CODE | 🔒 LOCKED |
| 8.14 | Booking Intent UX Signals & Legal Disclaimers | NO CODE | 🔒 LOCKED |

---

## ⏭️ Next Module

**Module 9** — Ratings & Reviews (Post-Interaction)

This module will define:
- Review eligibility rules
- One review per interaction
- Rating aggregation
- Abuse prevention
- Moderation hooks






