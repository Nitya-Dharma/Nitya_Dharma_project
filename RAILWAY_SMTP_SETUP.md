# Set Up SMTP on Railway for Email Verification (Pandit Registration)

To receive **real verification emails** for pandit (and user) registration on Railway, set these environment variables and redeploy.

---

## Step 1: Open Railway variables

1. Go to [Railway Dashboard](https://railway.app/dashboard).
2. Open your **project** → select your **service** (the Django app).
3. Go to the **Variables** tab (or **Settings** → **Variables**).

---

## Step 2: Add these variables

Add **all** of the following. Replace the example values with your own.

| Variable | Example value | Required |
|----------|----------------|----------|
| `EMAIL_HOST` | `smtp.gmail.com` | Yes |
| `EMAIL_PORT` | `587` | No (default 587) |
| `EMAIL_USE_TLS` | `True` | No (default True) |
| `EMAIL_HOST_USER` | `yourname@gmail.com` | Yes |
| `EMAIL_HOST_PASSWORD` | Your Gmail **App Password** (see below) | Yes |
| `DEFAULT_FROM_EMAIL` | `yourname@gmail.com` | **Yes for Gmail** (must equal `EMAIL_HOST_USER`) |

- **Gmail:** `DEFAULT_FROM_EMAIL` **must** be the same as `EMAIL_HOST_USER`, or Gmail may drop the email.
- **Other providers:** Use the “From” address they allow (often the same as the SMTP login).

---

## Step 3: Gmail App Password (if using Gmail)

Gmail does **not** accept your normal account password for SMTP. Use an **App Password**:

1. Turn on **2-Step Verification** for your Google account (if not already):
   - [Google Account → Security → 2-Step Verification](https://myaccount.google.com/security)
2. Create an App Password:
   - Go to [Google Account → Security → App passwords](https://myaccount.google.com/apppasswords)
   - Select app: **Mail**, device: **Other** (e.g. “Nitya Dharma Railway”)
   - Click **Generate**. Copy the **16-character password** (no spaces).
3. In Railway, set:
   - `EMAIL_HOST_PASSWORD` = that 16-character App Password
   - `EMAIL_HOST_USER` = your full Gmail address (e.g. `yourname@gmail.com`)
   - `DEFAULT_FROM_EMAIL` = same as `EMAIL_HOST_USER`

---

## Step 4: Redeploy

After saving the variables:

- Railway usually **redeploys automatically**. If not, trigger a **Redeploy** from the **Deployments** tab.

Wait until the new deployment is **Success** before testing.

---

## Step 5: Test

1. Open your Railway app URL (e.g. `https://your-app.up.railway.app`).
2. Register a **new pandit** (or user) using an email address you can access.
3. Check that inbox (and spam) for the **verification email** from `DEFAULT_FROM_EMAIL`.

If no email arrives:

- Check **Railway logs** (Deployments → View Logs) for email-related errors.
- Confirm all variables are set and that you **redeployed** after adding them.
- For Gmail, confirm `DEFAULT_FROM_EMAIL` and `EMAIL_HOST_USER` are identical.

---

## Using another provider (SendGrid, Mailgun, etc.)

Your app only needs the standard Django SMTP variables. Example for **SendGrid**:

| Variable | Example |
|----------|---------|
| `EMAIL_HOST` | `smtp.sendgrid.net` |
| `EMAIL_PORT` | `587` |
| `EMAIL_HOST_USER` | `apikey` |
| `EMAIL_HOST_PASSWORD` | Your SendGrid API key |
| `DEFAULT_FROM_EMAIL` | A verified sender in SendGrid (e.g. `noreply@yourdomain.com`) |

Use your provider’s docs for host, port, and TLS. Same variables go into Railway → Variables, then redeploy.
