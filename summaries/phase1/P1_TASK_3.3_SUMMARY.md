# Task 3.3 - Referral Link Generation & Lifecycle Summary

## Overview
Successfully implemented referral link generation and lifecycle management for the Nitya Dharma platform. This provides backend endpoints for Admin Pandits and Super Admins to generate and deactivate referral links, with strict access control and full audit trail. **ONLY BACKEND was implemented** - no frontend templates, dashboards, or registration logic.

## Changes Made

### 1. Created Referral Views
**File:** `referrals/views.py` (newly created)

**Views:**
- `generate_referral_link()` - Generate new referral link with unique token and code
- `deactivate_referral_link()` - Deactivate an existing referral link

**Helper Functions:**
- `_can_generate_referral(user)` - Check if user can generate referral links
- `_generate_unique_token()` - Generate unique, URL-safe hexadecimal token

---

### 2. Created Referral URLs
**File:** `referrals/urls.py` (newly created)

**URL Patterns:**
- `POST /referrals/generate/` - Generate new referral link
- `POST /referrals/<id>/deactivate/` - Deactivate referral link

**Access Control:**
- All endpoints require `@admin_required` decorator
- Additional checks for `status='active'` and `is_superuser`

---

### 3. Updated Project URLs
**File:** `nityadharma/urls.py`

**Change:** Added `path('referrals/', include('referrals.urls'))`

**Purpose:**
- Enable referral endpoints in project
- Maintain clean URL structure

---

## Access Control Implementation

### Who Can Generate Referral Links

**Authorized:**
- ✅ **Super Admins** (`is_superuser=True`)
- ✅ **Admin Pandits** (`role='admin'`, `status='active'`, `is_active=True`)

**Not Authorized:**
- ❌ **Regular Active Pandits** (`role='pandit'`, `status='active'`)
- ❌ **Pending Admin Pandits** (`role='admin'`, `status='pending'`)
- ❌ **Rejected Admin Pandits** (`role='admin'`, `status='rejected'`)
- ❌ **Inactive Users** (`is_active=False`)
- ❌ **Regular Users** (`role='user'`)

**Enforcement:**
- `@admin_required` decorator (from `accounts.decorators`)
- `_can_generate_referral()` function checks:
  - Super Admin status OR
  - Admin role AND active status AND is_active flag

**Contract:**
- ✅ Only Admin Pandits (active) and Super Admins can generate
- ✅ Status check is mandatory (must be 'active')
- ✅ is_active flag check is mandatory
- ✅ Regular Pandits cannot generate (even if active)

---

## Referral Link Generation

### Token and Code Generation

**Process:**
1. Generate 32-byte random token using `secrets.token_hex(32)`
2. Convert to hexadecimal (64 characters)
3. Use as both token and referral_code (must match)
4. Ensure uniqueness (retry if collision)

**Properties:**
- **Token:** Unique, URL-safe hexadecimal string
- **Referral Code:** Same as token (must match for registration)
- **Uniqueness:** Enforced by database unique constraint
- **Security:** Cryptographically secure random generation

**Contract:**
- ✅ Token and code are unique and secure
- ✅ Token and code must match for registration
- ✅ Uniqueness is guaranteed by database constraint

---

### Referral Link Properties

**Default Values:**
- `max_uses = 5` (enforced by model default)
- `used_count = 0` (starts at zero)
- `is_active = True` (starts active)
- `created_by = request.user` (Admin Pandit or Super Admin)

**Audit Data:**
- Creator (User FK)
- Token (unique)
- Referral Code (unique, matches token)
- Created timestamp
- Updated timestamp

**Contract:**
- ✅ Maximum 5 uses per link (default)
- ✅ Starts with 0 uses
- ✅ Starts as active
- ✅ Full audit trail recorded

---

## Referral Link Lifecycle

### Active State

**Referral link is active when:**
- `is_active = True`
- `used_count < max_uses`
- `expires_at` is None or in the future

**Can be used for registration:**
- ✅ Active referral links can be used
- ✅ Usage count is tracked
- ✅ Auto-deactivation when limit reached (Task 3.4)

---

### Deactivation

**Manual Deactivation:**
- Admin Pandit or Super Admin can deactivate any referral link
- Sets `is_active = False`
- Link cannot be used for new registrations
- Existing usage records remain for audit

**Auto-Deactivation:**
- When `used_count >= max_uses` (handled in Task 3.4)
- Link becomes inactive automatically
- Cannot be reactivated (must generate new link)

**Contract:**
- ✅ Manual deactivation is available
- ✅ Auto-deactivation on usage limit (Task 3.4)
- ✅ Deactivated links cannot be used
- ✅ Usage records are preserved for audit

---

## API Endpoints

### 1. Generate Referral Link

**Endpoint:** `POST /referrals/generate/`

**Access:** Admin Pandit (active) or Super Admin

**Request:**
- Method: POST
- Body: Optional JSON (currently no parameters)

**Response (Success - 201):**
```json
{
  "success": true,
  "message": "Referral link generated successfully",
  "referral_link": {
    "id": 1,
    "token": "abc123def456...",
    "referral_code": "abc123def456...",
    "url": "/accounts/pandit/register/abc123def456.../",
    "max_uses": 5,
    "used_count": 0,
    "is_active": true,
    "created_at": "2024-01-01T12:00:00Z",
    "created_by": {
      "id": 1,
      "email": "admin@example.com",
      "role": "admin",
      "status": "active"
    }
  }
}
```

**Response (Error - 403):**
```json
{
  "error": "Access denied",
  "message": "Only Admin Pandits (active) and Super Admins can generate referral links",
  "user_role": "pandit",
  "user_status": "active",
  "is_superuser": false
}
```

---

### 2. Deactivate Referral Link

**Endpoint:** `POST /referrals/<id>/deactivate/`

**Access:** Admin Pandit (active) or Super Admin

**Request:**
- Method: POST
- URL Parameter: `referral_link_id` (integer)

**Response (Success - 200):**
```json
{
  "success": true,
  "message": "Referral link 1 deactivated successfully",
  "referral_link": {
    "id": 1,
    "token": "abc123de...",
    "is_active": false,
    "used_count": 2,
    "max_uses": 5,
    "deactivated_at": "2024-01-01T12:00:00Z"
  }
}
```

**Response (Error - 400):**
```json
{
  "error": "Already inactive",
  "message": "Referral link 1 is already inactive",
  "referral_link": {
    "id": 1,
    "token": "abc123de...",
    "is_active": false,
    "used_count": 2,
    "max_uses": 5
  }
}
```

---

## Security & Validation

### Access Control

**Enforcement:**
- `@admin_required` decorator (requires authentication and admin role)
- `_can_generate_referral()` function (checks status and is_active)
- Super Admin bypass (always allowed)

**Checks:**
- ✅ User is authenticated
- ✅ User has admin role OR is superuser
- ✅ User status is 'active' (for Admin Pandits)
- ✅ User is_active flag is True

**Contract:**
- ✅ Access control is enforced at view level
- ✅ Multiple layers of validation
- ✅ Clear error messages for unauthorized access

---

### Token Generation Security

**Method:**
- Uses `secrets.token_hex()` (cryptographically secure)
- 32-byte random generation (64 hex characters)
- Uniqueness enforced by database constraint

**Properties:**
- Cryptographically secure random
- URL-safe (hexadecimal)
- Unique (database constraint)
- Collision-resistant (retry logic)

**Contract:**
- ✅ Secure token generation
- ✅ Uniqueness guaranteed
- ✅ URL-safe format

---

## Integration with Previous Modules

### Module 1 (User & Role System)
- ✅ Uses `@admin_required` decorator from `accounts.decorators`
- ✅ Uses `is_admin()` function from `accounts.utils`
- ✅ Checks User model role and status fields
- ✅ Respects authentication system

### Module 2 (Pandit Onboarding)
- ✅ Referral links support referral-based registration (Task 2.2)
- ✅ No changes to approval workflow
- ✅ Referral generation is separate from approval

### Module 3 (This Module)
- ✅ Task 3.1: Strategy documented and locked
- ✅ Task 3.2: Models created
- ✅ Task 3.3: Generation implemented (this task)
- ✅ Task 3.4: Referral validation in registration (next task)

---

## Lifecycle Enforcement

### How Referral Lifecycle is Enforced

**Generation:**
- Only Admin Pandits (active) or Super Admins can generate
- Each link has max_uses=5, used_count=0, is_active=True
- Token and code are generated securely and uniquely

**Usage:**
- Usage tracking will be in Task 3.4 (during registration)
- used_count increments with each registration
- Auto-deactivation when used_count >= max_uses

**Deactivation:**
- Manual deactivation available (this task)
- Auto-deactivation on usage limit (Task 3.4)
- Deactivated links cannot be used

**Contract:**
- ✅ Lifecycle rules are enforced
- ✅ Usage limits are tracked
- ✅ Deactivation is available
- ✅ Audit trail is maintained

---

## Why Generation is Restricted to Admin Roles

### 1. Quality Control
**Why:**
- Ensures only trusted Pandits can invite others
- Maintains platform quality standards
- Prevents spam registrations

**Benefits:**
- Controlled growth
- Quality assurance
- Trust network building

---

### 2. Spam Prevention
**Why:**
- Limits referral generation to vetted admins
- Prevents unlimited invite abuse
- Maintains platform credibility

**Benefits:**
- Prevents spam
- Limits abuse potential
- Maintains security

---

### 3. Accountability
**Why:**
- Admin Pandits are responsible for their referrals
- Full audit trail of who generated what
- Easy to identify problematic referrers

**Benefits:**
- Clear accountability
- Audit trail
- Moderation support

---

### 4. Trust Network
**Why:**
- Builds organic growth through trusted channels
- Creates transparent referral network
- Maintains platform integrity

**Benefits:**
- Organic growth
- Trust network
- Platform credibility

---

## Validation Checklist

### Permission Checks
- ✅ Regular Pandit → ❌ blocked
- ✅ Pending Pandit → ❌ blocked
- ✅ Admin Pandit (active) → ✅ allowed
- ✅ Admin Pandit (pending) → ❌ blocked
- ✅ Admin Pandit (rejected) → ❌ blocked
- ✅ Super Admin → ✅ allowed

### Lifecycle Checks
- ✅ Token & hex code generated
- ✅ Max uses = 5 enforced
- ✅ Manual deactivation works
- ✅ Auto-deactivation (Task 3.4)

### Safety Checks
- ✅ No public endpoints exposed (all require auth)
- ✅ No registration logic added
- ✅ No frontend created
- ✅ No dashboard UI

---

## Rules Compliance

### ✅ Backend Only
- ✅ No frontend templates created
- ✅ No dashboards created
- ✅ No public endpoints
- ✅ JSON responses only

### ✅ Access Control
- ✅ Only Admin Pandits (active) and Super Admins can generate
- ✅ Status check is mandatory
- ✅ is_active flag check is mandatory
- ✅ Clear error messages

### ✅ Lifecycle Management
- ✅ Generation works correctly
- ✅ Deactivation works correctly
- ✅ Auto-deactivation (Task 3.4)
- ✅ Audit trail maintained

---

## Next Steps

**Task 3.3 is complete and locked.**

Ready to proceed to:
- **Module 3 → Task 3.4:** Referral validation during Pandit registration

**Important:**
- Referral generation is implemented
- Access control is enforced
- Lifecycle management is ready
- Auto-deactivation will be in Task 3.4

---

## Notes

- ✅ Referral generation is restricted to Admin/Super Admin
- ✅ Token and code generation is secure
- ✅ Lifecycle rules are enforced
- ✅ Access control is strict
- ✅ System check passes with no issues
- ✅ Ready for Task 3.4 (Referral validation)

---

**Status:** ✅ Task 3.3 Complete - Referral Link Generation & Lifecycle Implemented
**Module 3:** Task 3.3 COMPLETE
**Ready for:** Task 3.4 - Referral Validation During Pandit Registration











