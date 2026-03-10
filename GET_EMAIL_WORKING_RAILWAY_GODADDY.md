# How to Get Emails in Your Mailbox (Railway, GoDaddy, VPS, All Servers)

Emails will **only be delivered to your mailbox** when the app is configured correctly **on the server** where it runs. Use one of the options below and set the variables **on that host** (Railway dashboard, GoDaddy env, VPS `.env`, etc.).

**Quick check:** After setting variables and redeploying/restarting, run:
`python manage.py check_production_config`  
You should see either **"SMTP email is configured"** or **"Resend is configured"**. If you see **"Console backend"**, emails are not being sent to real mailboxes.

---

## Railway (recommended: Resend — SMTP is often blocked)

Railway Free/Hobby plans often **block outbound SMTP** (port 587). Use **Resend** (HTTPS API) so emails still reach mailboxes.

1. Sign up at [resend.com](https://resend.com) and get an API key.
2. In **Railway** → your service → **Variables**, add:
   - `RESEND_API_KEY` = your API key (e.g. `re_xxxx`)
   - `RESEND_FROM_EMAIL` = `Nitya Dharma <onboarding@resend.dev>` (or your verified domain)
3. Do **not** set `EMAIL_HOST` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` if you use Resend (Resend takes priority).
4. Redeploy. Run `check_production_config` and confirm "Resend is configured".
5. Test: register a Pandit and check inbox + spam.

---

## Option A: Use Gmail (works from GoDaddy, VPS; Railway may block SMTP)

Gmail SMTP works from any server. You don’t need a server on GoDaddy to use Gmail.

### 1. Create a Gmail App Password

1. Turn on **2-Step Verification**: [Google Account → Security → 2-Step Verification](https://myaccount.google.com/security)
2. Create an **App Password**: [App passwords](https://myaccount.google.com/apppasswords)  
   - App: **Mail**  
   - Device: **Other** (e.g. “Nitya Dharma”)  
   - Click **Generate** and copy the **16-character** password (no spaces).

### 2. Set variables on your host

Use the **exact** variable names below. Replace with your own Gmail and the 16-character App Password.

| Variable | Value |
|----------|--------|
| `EMAIL_HOST` | `smtp.gmail.com` |
| `EMAIL_PORT` | `587` |
| `EMAIL_USE_TLS` | `True` |
| `EMAIL_HOST_USER` | `yourname@gmail.com` |
| `EMAIL_HOST_PASSWORD` | `xxxxxxxxxxxxxxxx` (the 16-character App Password) |
| `DEFAULT_FROM_EMAIL` | `yourname@gmail.com` **(must be same as EMAIL_HOST_USER)** |

**Where to set them:**

- **Railway:** Project → your service (Django app) → **Variables** tab → Add each variable → Save (redeploy will start).
- **GoDaddy (cPanel):** Your app’s environment / **Environment Variables** (or `.env` if you load it) → Add the same names and values.
- **GoDaddy (Plesk):** Same idea: environment variables for the app / PHP or Python runtime.
- **VPS / Docker:** Export in shell or put in `.env` and load it; never commit `.env` to Git.

### 3. Redeploy / restart

- **Railway:** Wait for redeploy to finish (or trigger **Redeploy**).
- **GoDaddy / other:** Restart the app or web server so it reads the new variables.

### 4. Test

1. Open your **live** site (Railway or GoDaddy URL).
2. Register a **new Pandit** (or user) with an email you can access.
3. Check **inbox** and **spam** for the verification email.

---

## Option B: Use GoDaddy’s own SMTP (if your domain/email is on GoDaddy)

If you have email hosted at GoDaddy (e.g. `you@yourdomain.com`), you can use their SMTP from the same app (Railway or GoDaddy server).

1. In **GoDaddy**: Product → **Email** → open the mailbox you want to use for sending.
2. Find **SMTP settings** (often under “Settings” or “Configure”):
   - **Outgoing server:** often `smtpout.secureserver.net` or `smtp.secureserver.net`
   - **Port:** 465 (SSL) or 587 (TLS)
   - **Username:** full email (e.g. `you@yourdomain.com`)
   - **Password:** the mailbox password (or app password if they offer it)

3. Set these **on the host** (all three required for SMTP). For **port 465** use `EMAIL_USE_SSL=True` and `EMAIL_USE_TLS=False`:

| Variable | Port 587 (TLS) | Port 465 (SSL) |
|----------|----------------|----------------|
| `EMAIL_HOST` | `smtpout.secureserver.net` | `smtpout.secureserver.net` |
| `EMAIL_PORT` | `587` | `465` |
| `EMAIL_USE_TLS` | `True` | `False` |
| `EMAIL_USE_SSL` | `False` | `True` |
| `EMAIL_HOST_USER` | `you@yourdomain.com` | `you@yourdomain.com` |
| `EMAIL_HOST_PASSWORD` | mailbox password | mailbox password |
| `DEFAULT_FROM_EMAIL` | `you@yourdomain.com` | `you@yourdomain.com` |

4. Redeploy/restart, then test registration and check inbox + spam.

---

## Option C: SendGrid / Mailgun (for higher volume or custom domain)

- **SendGrid:** Create an API key, then set:
  - `EMAIL_HOST` = `smtp.sendgrid.net`
  - `EMAIL_PORT` = `587`
  - `EMAIL_HOST_USER` = `apikey`
  - `EMAIL_HOST_PASSWORD` = your SendGrid API key
  - `DEFAULT_FROM_EMAIL` = a verified sender in SendGrid (e.g. `noreply@yourdomain.com`)

- **Mailgun:** Use the SMTP credentials Mailgun gives you and set the same variable names on your host.

---

## Check that the app “sees” SMTP

After setting variables and redeploying/restarting, you can confirm the app is using SMTP:

**On Railway:**

```bash
railway ssh -- python manage.py check_production_config
```

**Locally (against prod settings):**

```powershell
$env:DJANGO_SETTINGS_MODULE="nityadharma.settings.prod"
python manage.py check_production_config
```

Look for:

- `EMAIL_HOST set: True`
- `EMAIL_HOST_USER set: True`
- `EMAIL_HOST_PASSWORD set: True`
- `=> SMTP email is configured (emails will be sent).`

If you see `=> Console/other backend`, one of the three required variables is still missing or not loaded on that environment.

---

## Quick checklist

- [ ] **Railway:** `RESEND_API_KEY` and `RESEND_FROM_EMAIL` set. **GoDaddy/VPS:** `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` set.
- [ ] For Gmail: `DEFAULT_FROM_EMAIL` = `EMAIL_HOST_USER` (same address)
- [ ] App restarted or redeployed after changing variables
- [ ] Tested with a **new** Pandit registration and checked inbox + spam
- [ ] `check_production_config` shows SMTP or Resend and saw “SMTP email is configured”

## Emails still not in mailbox?

- **Check backend:** Run `python manage.py check_production_config`. You must see "SMTP email is configured" or "Resend is configured". If "Console backend", set env vars on that host and restart/redeploy.
- **Spam folder:** Check Spam/Junk; mark as Not Spam.
- **Gmail:** `DEFAULT_FROM_EMAIL` must equal `EMAIL_HOST_USER`.
- **GoDaddy 465:** Use `EMAIL_PORT=465`, `EMAIL_USE_SSL=True`, `EMAIL_USE_TLS=False`.
- **Railway:** Use Resend (`RESEND_API_KEY` + `RESEND_FROM_EMAIL`); SMTP is often blocked.

Once configured, emails will be sent and can appear in your mailbox on Railway, GoDaddy, VPS, and all servers.
