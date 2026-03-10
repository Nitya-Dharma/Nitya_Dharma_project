# Why am I not getting Pandit registration emails?

Pandit registration sends a **verification email** to the email address the Pandit used to register. If you never see it, follow this checklist.

---

## 1. Configure SMTP on Railway (required for real emails)

If **EMAIL_HOST**, **EMAIL_HOST_USER**, and **EMAIL_HOST_PASSWORD** are **not** set on Railway, the app uses the **console** backend: emails are **not** sent to real inboxes (they only appear in server logs).

**Do this:**

1. **Railway** → your project → **Web service** (Django app) → **Variables**.
2. Add (replace with your values):

   | Variable | Value |
   |----------|--------|
   | `EMAIL_HOST` | `smtp.gmail.com` |
   | `EMAIL_PORT` | `587` |
   | `EMAIL_USE_TLS` | `True` |
   | `EMAIL_HOST_USER` | Your Gmail address (e.g. `you@gmail.com`) |
   | `EMAIL_HOST_PASSWORD` | Gmail **App Password** (16 characters, from [App passwords](https://myaccount.google.com/apppasswords)) |
   | `DEFAULT_FROM_EMAIL` | **Same as EMAIL_HOST_USER** (required for Gmail) |

3. **Redeploy** the service (Railway often redeploys when you save variables).
4. Wait for the deployment to finish, then test again.

Details: see **RAILWAY_SMTP_SETUP.md**.

---

## 2. Check that the app is using SMTP

On your PC (with Railway CLI linked) or after SSH into the service, run:

```powershell
railway ssh -- python manage.py check_production_config
```

Look at the **Email** section:

- If it says **"SMTP email is configured"** → SMTP is on; the problem is likely Gmail rules, spam, or the recipient address.
- If it says **"Console/other backend"** → set the three variables in step 1 and redeploy.

---

## 3. Send a test email (verify SMTP without registering again)

After setting the variables and redeploying, send one test email to an address you control:

```powershell
railway ssh -- python manage.py send_test_email your@gmail.com
```

- If you see **"Sent test email to ..."** and the message arrives (inbox or spam), SMTP is working. Then Pandit verification emails will go to the **Pandit’s** email (the one they used when registering).
- If it fails, the command will show an error (e.g. wrong App Password, TLS, or host).

---

## 4. Where does the Pandit email go?

The **verification email** is sent to the **email address the Pandit entered** when they registered, **not** to you or to an admin inbox.

- Check that the Pandit is looking at the **correct inbox** (the one they used to register).
- Check **Spam / Junk** for that address.
- If you are testing with your own email, register the Pandit using **that same** email so the verification goes to you.

---

## 5. Gmail: DEFAULT_FROM_EMAIL must match EMAIL_HOST_USER

If you use Gmail and **DEFAULT_FROM_EMAIL** is different from **EMAIL_HOST_USER**, Gmail can **silently drop** messages. Set:

- `DEFAULT_FROM_EMAIL` = same value as `EMAIL_HOST_USER` (e.g. `you@gmail.com`).

---

## 6. Check Railway logs for errors

1. **Railway** → your **Web service** → **Deployments** → open the latest deployment.
2. Click **View Logs**.
3. Register a Pandit (or run `send_test_email`), then look for lines containing:
   - `EMAIL`
   - `send_mail`
   - `CRITICAL` / `Error` / `Failed`

Those messages will show whether the server is trying to send and if SMTP is failing.

---

## Quick checklist

- [ ] **EMAIL_HOST**, **EMAIL_HOST_USER**, **EMAIL_HOST_PASSWORD** set on Railway (Web service Variables).
- [ ] **DEFAULT_FROM_EMAIL** = **EMAIL_HOST_USER** (for Gmail).
- [ ] **Redeployed** after changing variables.
- [ ] **check_production_config** shows “SMTP email is configured”.
- [ ] **send_test_email** succeeds and you receive the test at the given address.
- [ ] Pandit is checking the **same email** they used to register (and spam folder).

Once SMTP is configured and the test email is received, Pandit registration emails will go to each Pandit’s email address.
