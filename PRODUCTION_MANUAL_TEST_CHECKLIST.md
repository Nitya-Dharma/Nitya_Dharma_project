# Production Manual Test Checklist — Nitya Dharma

Use this checklist after deploying to Railway (or any production) to ensure all operations that work on localhost also work in production. It also explains how to fix common issues (500 errors, emails not sending).

---

## 1. Before You Test — Production Environment Variables

Set these in **Railway → Your Service → Variables** (or your host’s env):

| Variable | Required | Purpose |
|----------|----------|---------|
| `SECRET_KEY` | Yes | Django secret (use a long random string). |
| `DEBUG` | Yes | Set to `False` in production. |
| `MYSQL_URL` or `DATABASE_URL` | Yes | Database connection string. |
| `ALLOWED_HOSTS` | Optional | Comma-separated; Railway adds `.railway.app` if not set. |
| **Email (needed for verification, password reset, etc.)** | | |
| `EMAIL_HOST` | For real email | e.g. `smtp.gmail.com`. |
| `EMAIL_PORT` | Optional | Default 587. |
| `EMAIL_USE_TLS` | Optional | Default True. |
| `EMAIL_HOST_USER` | For real email | Your SMTP login (e.g. Gmail address). |
| `EMAIL_HOST_PASSWORD` | For real email | App password or SMTP password. |
| `DEFAULT_FROM_EMAIL` | Optional | **For Gmail, set equal to `EMAIL_HOST_USER`** or emails may be dropped. |

If email variables are **not** set, the app uses the **console** backend: no crash, but emails are not sent (they only appear in server logs). To get real emails in production, set the variables above and redeploy.

---

## 2. Fixing 500 Errors (e.g. Django Admin “Activate User”)

- **Check Railway logs** (Deployments → View Logs) for the exact traceback when the 500 occurs.
- **Common causes:**
  - **Missing email config:** The app now falls back to the console backend if SMTP is not set, so this should not crash. If you see an email-related error in logs, set `EMAIL_*` as in section 1.
  - **Missing template or static file:** Fix by adding the template/static or changing the view (as was done for master data upload).
  - **Database or migration issue:** Run `railway run python manage.py migrate` (or `railway ssh -- python manage.py migrate` if your CLI can’t reach DB).
  - **Context processor or middleware:** Logs will show the failing line; fix that module or make it safe when data is missing.
- **Admin “Activate user”:** Toggling `is_active` in Django admin only saves the user; it does not send email by default. If you still get 500, the traceback in Railway logs will point to the real cause (e.g. a signal, custom admin code, or a dependency).

---

## 3. Manual Test Areas and Expected Results

### 3.1 Authentication

| # | What to do | Test data / steps | Expected result |
|---|------------|-------------------|-----------------|
| 1 | **Login** | Use Super Admin (or any) email + password. | Redirect to home (or intended page); no 500. |
| 2 | **Logout** | Click Logout. | Redirect to login or home; session cleared. |
| 3 | **Password reset request** | Go to “Forgot password”, enter an existing user email. | If email is configured: email received with reset link. If not: no error; check logs for “console” email. |
| 4 | **Password reset confirm** | Open link from email, set new password. | Success message; can log in with new password. |

---

### 3.2 User Registration (End User)

| # | What to do | Test data / steps | Expected result |
|---|------------|-------------------|-----------------|
| 1 | **Register as User** | New email, e.g. `testuser@example.com`, password, first/last name. | Account created; message to check email to verify. |
| 2 | **Email verification** | Open verification link from email (or from logs if using console backend). | “Email verified” message; redirect to login. |
| 3 | **Login after verification** | Log in with same email/password. | Login succeeds; user can use the site. |

**Note:** If emails are not configured, verification links won’t be sent; use “resend verification” or check server logs for the link in console backend output.

---

### 3.3 Pandit Registration and Approval

| # | What to do | Test data / steps | Expected result |
|---|------------|-------------------|-----------------|
| 1 | **Register as Pandit** | Use Pandit registration flow (e.g. with referral link if required). | User created with role=pandit, status=pending, is_active=False. |
| 2 | **Verification email** | Same as user: check inbox or logs for verification link. | Link works; email verified; account still pending. |
| 3 | **Approve Pandit** | As Admin/Super Admin, open pending Pandits list and approve the test Pandit. | Pandit status=active, is_active=True; success message. |
| 4 | **Pandit login** | Log in as the approved Pandit. | Login succeeds; Pandit dashboard/features available. |

---

### 3.4 Django Admin

| # | What to do | Test data / steps | Expected result |
|---|------------|-------------------|-----------------|
| 1 | **Admin login** | Go to `/admin/`, log in as Super Admin (is_staff=True). | Admin index loads; no 500. |
| 2 | **List users** | Open “Users” (accounts.User). | User list loads. |
| 3 | **Edit user (e.g. activate)** | Open a user, check “Active” (is_active), click Save. | “User saved” message; no 500. If 500, check Railway logs (see section 2). |
| 4 | **Change password (admin)** | User change form → “this form” password link, set new password. | Password changed; user can log in with new password. |

---

### 3.5 File Uploads

| # | What to do | Test data / steps | Expected result |
|---|------------|-------------------|-----------------|
| 1 | **Master data — Cities CSV** | Super Admin → Master Data Management → Cities tab. Upload a CSV with columns: `name,state,status`. Example: `Mumbai,Maharashtra,active` (with header row). | Success message with inserted/skipped/failed counts; cities appear in system. |
| 2 | **Master data — Mandals** | Mandals tab; CSV: `city,name,status` (e.g. `Mumbai,Andheri,active`). | Upload succeeds; mandals listed. |
| 3 | **Master data — Local areas** | Local Areas tab; CSV: `mandal,name,status` or as per your view (e.g. `city,mandal,name,status`). | Upload succeeds. |
| 4 | **Master data — Pooja categories / Poojas** | Upload CSVs per the format shown on the tab (e.g. `name,status` for categories; `name,pooja_category,status` for poojas). | Upload succeeds. |
| 5 | **Branding logo** | Super Admin → Branding / Logo upload; choose an image (e.g. PNG/JPG, within size limit). | Logo uploads and displays (or shows “None” if media is ephemeral and lost on redeploy; see project notes on persistent media). |
| 6 | **Profile picture** | As Pandit/User, upload profile picture in profile settings. | Upload succeeds; image visible where profile pictures are shown. |

---

### 3.6 File Downloads

| # | What to do | Test data / steps | Expected result |
|---|------------|-------------------|-----------------|
| 1 | **Sample CSV (Master data)** | Master Data Management → any tab → “Download Sample CSV”. | CSV file downloads (e.g. `cities_sample.csv`) with correct headers and example rows. |
| 2 | **Data export (Super Admin)** | Super Admin → Data Export (or equivalent). | Export starts or file downloads per your feature (no 500). |

---

### 3.7 Emails (Production)

| # | What to do | Test data / steps | Expected result |
|---|------------|-------------------|-----------------|
| 1 | **Verification email** | Register new user or Pandit. | If SMTP is set: email received with verification link. If not: no crash; link may be in server logs (console backend). |
| 2 | **Password reset email** | Request password reset for existing email. | If SMTP is set: email with reset link. If not: no crash. |
| 3 | **Optional: test script** | Run project’s `test_email_sending.py` or `test_email_delivery.py` against production settings (e.g. with `DJANGO_SETTINGS_MODULE=nityadharma.settings.prod`). | Script runs without error; if SMTP is set, test email is received. |

---

### 3.8 System Configuration (Super Admin)

| # | What to do | Test data / steps | Expected result |
|---|------------|-------------------|-----------------|
| 1 | **Open System Operational Settings** | Super Admin dashboard → System Operational Settings (e.g. `/dashboard/super-admin/system-operational-settings/`). | Page loads with the 6 config keys (rate limits, thresholds, limits). |
| 2 | **Change a value** | Change one value within min/max, submit. | Success message; value persists (e.g. after refresh). |
| 3 | **Other Super Admin pages** | Open Feature Flags, Kill Switch, Config Audit, Master Data, Notifications, Referrals, etc. | Each page loads and core actions work without 500. |

---

### 3.9 Other Critical Paths (Smoke)

| # | What to do | Expected result |
|---|------------|-----------------|
| 1 | **Home / public pages** | Load home, about, contact (if any). No 500. |
| 2 | **Search** | Perform a search (e.g. Pandits, poojas). Results or empty state; no 500. |
| 3 | **Pandit / Temple page** | Open a Pandit or temple page. Page loads; key widgets visible. |
| 4 | **Booking intent (if used)** | Create or view a booking intent. No 500. |
| 5 | **Contact / Support** | Submit contact form. Success message or email sent if configured. |

---

## 4. Test Data Snippets (Copy-Paste)

**Cities CSV (header + 3 rows):**
```text
name,state,status
Mumbai,Maharashtra,active
Delhi,Delhi,active
Bangalore,Karnataka,active
```

**Mandals CSV:**
```text
city,name,status
Mumbai,Andheri,active
Mumbai,Bandra,active
Delhi,Central Delhi,active
```

**Pooja categories CSV:**
```text
name,status
Daily & Common Household Poojas,active
House, Property & Vehicle Poojas,active
```

**Poojas CSV (use exact category name from your DB or upload categories first):**
```text
name,pooja_category,status
Ganapati Puja,Daily & Common Household Poojas,active
Satyanarayana Vratam,Daily & Common Household Poojas,active
```

**User registration:** Use a real email you control so you can receive verification and password-reset emails when SMTP is configured.

---

## 5. Quick Reference — URLs (adjust domain for production)

- Login: `/accounts/login/`
- Register (user): `/accounts/register/`
- Password reset: `/accounts/password-reset/`
- Django Admin: `/admin/`
- Super Admin dashboard: `/dashboard/super-admin/` (or as per your routes)
- Master Data Management: `/dashboard/super-admin/master-data/` or `/masterdata/` (as configured)
- System Operational Settings: `/dashboard/super-admin/system-operational-settings/`

---

## 6. After You Push to the Server

1. Set **production env vars** (section 1), especially `EMAIL_*` if you need real emails.
2. Run **migrations** on production DB (e.g. `railway ssh -- python manage.py migrate`).
3. Work through **sections 3.1–3.9** in order; note any 500 or missing email.
4. For any **500**, check **Railway logs** and fix the cause (section 2).
5. Re-test the failing case after each fix and redeploy if needed.

Once this checklist passes, the application is in a good state for production use; you can add more tests (e.g. payments, notifications) as needed.
