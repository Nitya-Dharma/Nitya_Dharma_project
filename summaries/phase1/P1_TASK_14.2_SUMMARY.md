# Task 14.2 — Event Taxonomy & Naming Conventions — COMPLETE

**Module:** 14 — Analytics & Telemetry  
**Task Type:** Architecture & Policy Definition (NO CODE)  
**Status:** ✅ COMPLETE

---

## Summary

Task 14.2 establishes event taxonomy and naming conventions for Module 14 — Analytics & Telemetry. This policy document ensures that all analytics events follow a consistent, neutral, and future-safe taxonomy, preventing hidden semantics from leaking into analytics and ensuring tools can be swapped without renaming logic.

---

## Key Deliverables

1. **Policy Document Created:**
   - `EVENT_TAXONOMY_NAMING_CONVENTIONS.md`

---

## Core Principles Established

### Event Naming Philosophy
**Key Principle:** Bad naming creates silent logic coupling. This task prevents that.

**Event taxonomy is a structural framework, not behavioral logic.**

**Names describe facts — never intent.**

**Event names are factual descriptors, not interpretations.**

**Event names must remain semantically sterile.**

---

## Formal Definition (LOCKED)

### Event Taxonomy IS:
- A shared naming contract
- A classification system
- A semantic boundary
- A tool-agnostic standard

**Key Rule:** Event taxonomy is a structural framework, not behavioral logic.

---

### Event Taxonomy is NOT:
- A behavior model
- A funnel definition
- A success metric
- A performance signal
- A recommendation input

**Key Rule:** Names describe facts — never intent.

---

## Event Naming Principles (LOCKED)

1. **Neutrality Principle:** Event names describe what happened, never why or how well.
   - ✅ `profile_viewed`
   - ❌ `interested_user_viewed_profile`

2. **Verb-Past-Tense Principle:** Events are recorded after completion. No predictive or future language.
   - ✅ `search_executed`
   - ❌ `search_intent_detected`

3. **Single-Action Principle:** One event = one action. No compound or inferred actions.
   - ✅ `availability_updated`
   - ❌ `pandit_became_active`

4. **Context-Free Principle:** Event names must be meaningful without UI context. No screen-specific semantics.

---

## Event Category Structure (LOCKED)

All events must fall into one and only one category:
- `user_*` — user-side actions
- `pandit_*` — pandit-side actions
- `admin_*` — admin / governance actions
- `system_*` — system-generated events (non-decision)

**Key Rule:** No hybrid or cross-role events allowed.

---

## Forbidden Event Patterns (LOCKED)

Events must NEVER:
- ❌ Encode quality (`high_quality_review`)
- ❌ Encode trust (`trusted_pandit_viewed`)
- ❌ Encode ranking (`top_result_clicked`)
- ❌ Encode success/failure meaning
- ❌ Encode user sentiment
- ❌ Encode governance intent

---

## Module Boundary Alignment

- **Module 7 (Search):** ❌ No ranking semantics
- **Module 10 (Trust Display):** ❌ No trust inference
- **Module 11 (Governance):** ❌ No decision meaning
- **Module 13 (Performance):** ❌ Not monitoring
- **Module 15 (Recommendations):** ❌ No signal source

---

## Validation Checklist — PASSED

- ✅ Event names are factual only
- ✅ No inferred meaning exists
- ✅ No cross-module semantics
- ✅ No intent or outcome language
- ✅ Tool-agnostic naming preserved

---

## Next Steps

Ready to proceed with **Task 14.3 — GTM / DataLayer Contract Definition (NO CODE)**.

---

## Notes

- This document establishes event taxonomy and naming conventions
- Bad naming creates silent logic coupling. This task prevents that
- Event taxonomy is a structural framework, not behavioral logic
- Names describe facts — never intent
- Event names are factual descriptors, not interpretations
- Event names must remain semantically sterile
- Common failures include: "conversion_completed", "successful_booking", "high_engagement_event", "trust_signal_emitted"
- If event names imply intent, quality, or outcomes, the design must be rejected




