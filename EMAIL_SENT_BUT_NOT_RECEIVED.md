# Email "Sent" But Not Received – What to Check

If your app says the email was sent (no error, logs show success) but it never appears in the inbox, work through these steps.

---

## 1. Check Spam / Junk / Promotions

- Look in **Spam** (or **Junk**), **Promotions** (Gmail), and **Other**.
- Search the mailbox for: **"Nitya Dharma"** or **"Verify your email"** or the exact recipient address.
- If you find it there: mark as **Not spam** and add the sender to contacts so future emails go to Inbox.

---

## 2. Gmail: FROM address must match (most common cause)

When using **Gmail SMTP**, the **From** address must be the same as the Gmail account you use to send. Otherwise Gmail can **silently drop** the message (no error, but no delivery).

**On Railway (or your host) set:**

| Variable | Must be |
|----------|--------|
| `EMAIL_HOST_USER` | `yourname@gmail.com` |
| `DEFAULT_FROM_EMAIL` | **Exactly** `yourname@gmail.com` (same as above) |

If `DEFAULT_FROM_EMAIL` is different (e.g. `noreply@nityadharma.com`) or missing, set it to the same value as `EMAIL_HOST_USER`, then **redeploy** and try again.

---

## 3. Confirm the recipient address

- Make sure the Pandit/user registered with the **correct email** (no typo).
- Try registering again with an email you know you can access (e.g. a second Gmail or Outlook) and see if that one receives the email.

---

## 4. Check Railway (or server) logs

After triggering a verification email, open **Railway → Deployments → View Logs** and look for:

- `[EMAIL DELIVERY] ✓ Email sent: FROM=... TO=...`  
  → Confirms the app thinks it sent to the right address.
- `FROM=... != EMAIL_HOST_USER=...` or **Gmail will silently drop**  
  → Then fix: set `DEFAULT_FROM_EMAIL` = `EMAIL_HOST_USER` (see step 2).
- Any SMTP error (e.g. authentication failed)  
  → Then fix: correct `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` (Gmail: use App Password).

---

## 5. Gmail: use App Password, not normal password

- **Normal Gmail password** must not be used for SMTP. Use an **App Password**.
- Create one: [Google Account → Security → App passwords](https://myaccount.google.com/apppasswords) (2-Step Verification must be on).
- Set `EMAIL_HOST_PASSWORD` to the **16-character** App Password (no spaces) on Railway/your host and redeploy.

---

## 6. Try a different recipient provider

- Send the verification email to an **Outlook / Yahoo / other** address.
- If it arrives there but not at Gmail, the problem is likely Gmail filtering or the From mismatch (step 2). If it doesn’t arrive anywhere, the issue may be SMTP config or the recipient address.

---

## 7. Quick checklist

- [ ] Checked **Spam**, **Junk**, **Promotions**, and search for "Nitya Dharma" or "Verify".
- [ ] **DEFAULT_FROM_EMAIL** = **EMAIL_HOST_USER** (for Gmail) and redeployed.
- [ ] **EMAIL_HOST_PASSWORD** is the Gmail **App Password** (16 characters).
- [ ] Recipient email has no typo; tried another address (e.g. different provider).
- [ ] Checked server logs for FROM/TO and any Gmail/SMTP warning.

Most “sent but not received” cases are either **spam folder** or **Gmail From mismatch** (step 2). Fix those first.
