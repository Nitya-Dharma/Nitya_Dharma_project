# Task 1.1 - User Model Strategy Documentation

## Overview
This document defines the User model strategy for the Nitya Dharma Pandit Listing Website. **This is a decision document only - NO CODE will be written in this task.**

---

## 1. Why a Custom User Model is REQUIRED

### ❌ Why NOT Use Default Django User Model

The default Django `User` model has these limitations:
- **Username-based authentication** - Not ideal for professional services
- **Limited fields** - Only `username`, `email`, `first_name`, `last_name`
- **No role system** - Cannot distinguish between regular users, pandits, and admins
- **No status tracking** - Cannot track pending/active/rejected states
- **Hard to extend later** - Changing user model after migrations is extremely painful

### ✅ Why Custom User Model is Required

For a **Pandit Listing Website**, we need:

1. **Role-Based Access Control**
   - Regular users (search and book pandits)
   - Pandits (provide services, manage profiles)
   - Admins (moderate, approve, manage referrals)

2. **Status Lifecycle Management**
   - Pandits need approval workflow (pending → active/rejected)
   - Users need account status tracking
   - Admin needs to control access

3. **Referral System Integration**
   - Track who referred which pandit
   - Build trust chain relationships
   - Link referrals to user accounts

4. **Review & Rating System**
   - Link reviews to specific users
   - Track reviewer identity
   - Prevent fake reviews

5. **Future Scalability**
   - Add pandit-specific fields (experience, specialization, etc.)
   - Add user preferences
   - Add booking history
   - Add payment integration

### 🚨 Critical Warning

**Once migrations are applied with the default User model, changing to a custom User model becomes extremely difficult and risky.** This is why we MUST decide NOW, before any data exists.

---

## 2. Authentication Identifier: Email vs Username

### Decision: ✅ **Email as Primary Login Identifier**

### Why Email?

1. **Professional Standard**
   - Pandits are professionals - email is more appropriate than username
   - Users expect email-based login in modern web applications
   - Email is already unique and verified

2. **User Experience**
   - Users don't need to remember a separate username
   - Email is easier to remember
   - Email verification can be added later for security

3. **Business Logic**
   - Email can be used for notifications
   - Email can be used for password resets
   - Email can be used for referral invitations

4. **Django Best Practice**
   - Django supports email-based authentication
   - Custom User model can use `USERNAME_FIELD = 'email'`
   - Cleaner than username-based auth

### Username: Display Only (Optional)

- Username can be a **display name** (optional field)
- Used for public profiles (e.g., "Pandit Rajesh Kumar")
- Not used for authentication
- Can be changed by user

### Implementation Strategy

```python
# Conceptual only - NO CODE YET
USERNAME_FIELD = 'email'  # Email is used for login
REQUIRED_FIELDS = []      # No additional required fields
```

---

## 3. Role Strategy

### Decision: ✅ **Single `role` Field on User Model**

### Role Values

1. **`user`** (Default)
   - Regular users who search and book pandits
   - Can write reviews
   - Can create booking requests
   - Cannot access pandit dashboard

2. **`pandit`**
   - Pandits who provide services
   - Can manage their profile
   - Can view booking requests
   - Can accept/reject bookings
   - Cannot access admin panel

3. **`admin`**
   - Platform administrators
   - Can approve/reject pandit registrations
   - Can generate referral links
   - Can moderate content
   - Full system access

### Why Single Field (Not Separate Models)?

1. **Simplicity**
   - One user can have one role
   - Easy to check: `if user.role == 'pandit'`
   - No complex joins needed

2. **Flexibility**
   - Easy to add new roles later (e.g., `moderator`, `super_admin`)
   - Role changes are simple (promote user to pandit)
   - No data migration complexity

3. **Django Best Practice**
   - Single model with role field is standard
   - Works well with Django permissions
   - Easy to extend with custom permissions

### Role Assignment Flow

- **New Registration:** Default role = `user`
- **Pandit Onboarding:** Role changes to `pandit` (after approval)
- **Admin Assignment:** Role manually set to `admin` (by superuser)

### Future Considerations

- Roles can be extended with Django permissions
- Custom permissions per role can be added
- Role-based decorators and mixins can be created

---

## 4. Status Strategy

### Decision: ✅ **Single `status` Field on User Model**

### Status Values

1. **`pending`**
   - New user registration (awaiting email verification)
   - Pandit registration (awaiting admin approval)
   - Account reactivation request

2. **`active`**
   - User account is active and verified
   - Pandit account is approved and active
   - Can use all features of their role

3. **`rejected`**
   - Pandit registration was rejected by admin
   - Account was suspended
   - Cannot log in or use platform

### Status Lifecycle

#### For Regular Users:
```
Registration → pending → active (after email verification)
```

#### For Pandits:
```
Registration → pending → active (after admin approval)
Registration → pending → rejected (if admin rejects)
```

#### For Admins:
```
Created by superuser → active (immediately)
```

### Why Status is Separate from Role?

- **Role** = What the user CAN do (user/pandit/admin)
- **Status** = Whether the user account is ACTIVE (pending/active/rejected)

Example:
- A user with `role='pandit'` and `status='pending'` cannot access pandit dashboard yet
- A user with `role='pandit'` and `status='rejected'` was rejected and cannot use platform
- A user with `role='pandit'` and `status='active'` can fully use pandit features

### Status Checks in Code

```python
# Conceptual only - NO CODE YET
if user.status == 'active' and user.role == 'pandit':
    # Allow pandit dashboard access
```

---

## 5. Impact on Future Modules

### Module 2: Pandit Onboarding
- **Impact:** User model must support role change from `user` → `pandit`
- **Requirement:** Status must support `pending` → `active` workflow
- **Dependency:** Custom User model with `role` and `status` fields

### Module 3: Referral & Trust Chain
- **Impact:** Referrals must link to User accounts
- **Requirement:** User model must support referral relationships
- **Dependency:** Custom User model allows adding referral fields later

### Module 4: Pandit Profile
- **Impact:** Profile must link to User model
- **Requirement:** User model must support one-to-one with PanditProfile
- **Dependency:** Custom User model allows clean relationships

### Module 5: Authorized Dashboard
- **Impact:** Dashboards must check `user.role` and `user.status`
- **Requirement:** Role-based access control
- **Dependency:** Custom User model with role field

### Module 6: Availability & Calendar
- **Impact:** Calendar must link to User (pandit)
- **Requirement:** User model must support foreign key relationships
- **Dependency:** Custom User model allows clean relationships

### Module 7: User Search & Discovery
- **Impact:** Search must filter by User (pandit) status
- **Requirement:** Only show active pandits
- **Dependency:** Status field on User model

### Module 8: Booking Intent
- **Impact:** Bookings must link to User (both user and pandit)
- **Requirement:** User model must support foreign key relationships
- **Dependency:** Custom User model allows clean relationships

### Module 9: Ratings & Reviews
- **Impact:** Reviews must link to User (reviewer)
- **Requirement:** User model must support foreign key relationships
- **Dependency:** Custom User model allows clean relationships

### Module 10: Public Trust Display
- **Impact:** Trust indicators must link to User
- **Requirement:** User model must support referral relationships
- **Dependency:** Custom User model allows adding referral fields

### Module 11: Admin Governance
- **Impact:** Admin must approve/reject based on User status
- **Requirement:** Status field must support workflow
- **Dependency:** Custom User model with status field

### Module 12: Security Hardening
- **Impact:** Security checks must verify User role and status
- **Requirement:** Role and status fields must be reliable
- **Dependency:** Custom User model with role and status

### Module 13: Performance & Cleanup
- **Impact:** Queries must efficiently filter by User role and status
- **Requirement:** Role and status fields must be indexed
- **Dependency:** Custom User model allows adding indexes

---

## 6. User Model Structure (Conceptual)

### Fields Required

1. **Authentication Fields**
   - `email` (Primary, unique, used for login)
   - `password` (Hashed, Django handles this)

2. **Profile Fields**
   - `first_name` (Optional)
   - `last_name` (Optional)
   - `username` (Optional, display name only)

3. **Role & Status Fields**
   - `role` (Choices: user, pandit, admin)
   - `status` (Choices: pending, active, rejected)

4. **Timestamps**
   - `date_joined` (When account was created)
   - `last_login` (Last login timestamp)
   - `updated_at` (Last profile update)

5. **Future Fields** (To be added in later modules)
   - Referral relationships
   - Pandit profile link
   - Booking history
   - Review history

### Model Relationships (Future)

- **One-to-One:** User → PanditProfile (if role is pandit)
- **One-to-Many:** User → Bookings (as customer)
- **One-to-Many:** User → Bookings (as pandit)
- **One-to-Many:** User → Reviews (as reviewer)
- **Many-to-Many:** User → Referrals (referral chain)

---

## 7. Settings Configuration (Future)

### AUTH_USER_MODEL Setting

```python
# Conceptual only - NO CODE YET
# In settings/base.py:
AUTH_USER_MODEL = 'accounts.User'
```

This tells Django to use our custom User model instead of the default one.

### Why This Must Be Set Early

- Must be set BEFORE first migration
- Cannot be changed after migrations
- All foreign keys will reference this model

---

## 8. Migration Strategy

### Step 1: Create Custom User Model
- Create `accounts` app
- Define custom User model
- Set `AUTH_USER_MODEL` in settings
- Create initial migration

### Step 2: Apply Migration
- Run `python manage.py makemigrations`
- Run `python manage.py migrate`
- This creates the User table

### Step 3: Create Superuser
- Use `python manage.py createsuperuser`
- This creates the first admin user

### ⚠️ Critical: Do This BEFORE Any Other Models

- All other models will have foreign keys to User
- If User model changes later, all foreign keys break
- This is why we decide NOW, before any data exists

---

## 9. Decision Summary

### ✅ Locked Decisions

1. **Custom User Model:** ✅ REQUIRED
2. **Email Login:** ✅ Email is primary identifier
3. **Role Field:** ✅ Single field with choices (user, pandit, admin)
4. **Status Field:** ✅ Single field with choices (pending, active, rejected)
5. **App Name:** ✅ `accounts` app will contain User model

### 📋 Implementation Order

1. **Task 1.1:** ✅ Decision & Documentation (THIS TASK)
2. **Task 1.2:** Create Custom User Model (model only)
3. **Task 1.3:** Configure AUTH_USER_MODEL in settings
4. **Task 1.4:** Create and apply migrations
5. **Task 1.5:** Test User model creation
6. **Task 1.6:** Create superuser and verify

### 🚫 What We Will NOT Do

- ❌ Use default Django User model
- ❌ Use username for login
- ❌ Create separate models for each role
- ❌ Mix role and status into one field
- ❌ Delay this decision

---

## 10. Validation Checklist

Before proceeding to Task 1.2, verify:

- ✅ Custom User model decision is final
- ✅ Email login decision is justified
- ✅ Role strategy is simple and extensible
- ✅ Status lifecycle is clearly defined
- ✅ Impact on future modules is understood
- ✅ No code has been written yet
- ✅ All decisions are documented

---

## Conclusion

This strategy document locks the User model design before any code is written. This prevents the #1 Django mistake: changing the user model after migrations.

**Next Step:** Task 1.2 - Create Custom User Model (model only, no auth views)

---

**Status:** ✅ Task 1.1 Complete - Decisions Locked
**Date:** Task 1.1 completion
**Ready for:** Task 1.2 - Implementation












