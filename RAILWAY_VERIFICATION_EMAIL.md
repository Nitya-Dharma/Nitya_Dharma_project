# Get Verification Email on Railway (Production)

On Railway, outbound **SMTP is usually blocked**, so verification emails are not sent unless you use **Resend**. Follow these steps so users receive verification emails in production.

---

## Step 1: Configure Resend on Railway

1. **Get a Resend API key**
   - Sign up at [resend.com](https://resend.com) (free tier is enough).
   - Go to **API Keys** → **Create API Key** → copy the key (starts with `re_`).
   - **Sandbox:** With default "From" (`onboarding@resend.dev`), you can only send to the **email of your Resend account**. Use that email when testing registration.
   - **Production:** In Resend, add and **verify your domain**, then set the "From" to e.g. `noreply@yourdomain.com` so you can send to any address.

2. **Set variables on Railway**
   - Open your project on [railway.app](https://railway.app) → select your **Django app service** → **Variables**.
   - Add:
     - **`RESEND_API_KEY`** = your Resend API key (e.g. `re_xxxxxxxx`).
     - **`RESEND_FROM_EMAIL`** = `Nitya Dharma <onboarding@resend.dev>` (sandbox) or `Nitya Dharma <noreply@yourdomain.com>` (after domain verification).
   - Save. Railway will **redeploy** automatically.

3. **Confirm configuration**
   - After deploy, in Railway run:  
     `railway run python manage.py check_production_config`  
   - You should see: **"Resend is configured (emails will be sent via Resend API)."**  
   - If you still see "Console backend", the variables are not set or not loaded; check the Variables tab and redeploy.

After this, **new** Pandit registrations will receive verification emails, and any "resend verification" action will send via Resend.

---

## Step 2: Send verification email to an existing user (e.g. you)

If you already registered (e.g. `your-email@example.com`) but never got the email, send a **new** verification email from Railway:

1. **Resend must be configured** (Step 1).
2. **From your PC** (with Railway CLI linked to the project):
   ```bash
   railway run python manage.py resend_verification your-email@example.com
   ```
   Or in **Railway** → your service → **Settings** → run a one-off command, or use **Shell** if available, and run:
   ```bash
   python manage.py resend_verification kshruthi1167@gmail.com
   ```
3. Check the **inbox and spam** for that email and click the verification link.

---

## Step 3 (optional): Mark user as verified in Admin

If you need the user to log in immediately and cannot wait for the verification email:

1. Open **Django Admin** on Railway:  
   `https://web-production-7256f4.up.railway.app/admin/` (or your Railway URL + `/admin/`).
2. Log in as a **superuser**.
3. Go to **Users** → find the user (e.g. by email `your-email@example.com`) → open the user.
4. Check **Email verified** → Save.
5. The user can now log in without clicking the verification link.

Use this only for your own account or trusted users; normally prefer sending the verification email via Resend.

---

## Summary

| Goal | Action |
|------|--------|
| Verification emails work on Railway | Set `RESEND_API_KEY` and `RESEND_FROM_EMAIL` on Railway → redeploy. |
| New users get the email | Same as above; no extra step. |
| Resend email to existing user | Run `python manage.py resend_verification <email>` on Railway (after Resend is configured). |
| Let user log in without verifying | In Django Admin, set **Email verified** for that user. |

After Resend is configured, always check **spam** if the email does not appear in the inbox.
