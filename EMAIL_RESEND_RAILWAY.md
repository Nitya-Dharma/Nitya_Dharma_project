# Send Email on Railway Using Resend (Fix "Network is unreachable")

Railway **blocks outbound SMTP** (port 587) on Free/Trial/Hobby plans, so Gmail SMTP fails with **"Network is unreachable"**. Use **Resend** instead: it sends over **HTTPS** (port 443), which Railway allows.

---

## 1. Get a Resend API key

1. Sign up at **[resend.com](https://resend.com)** (free tier available).
2. Go to **API Keys** → **Create API Key** → copy the key (starts with `re_`).
3. **Sandbox:** With the default "From" (`onboarding@resend.dev`), you can only send **to the email address of your Resend account**. So use the same email you use for Pandit registration when testing.
4. **Production:** In Resend, add and **verify your domain**, then set **RESEND_FROM_EMAIL** to e.g. `Nitya Dharma <noreply@yourdomain.com>` so you can send to any recipient.

---

## 2. Set variables on Railway

In **Railway** → your **Django service** → **Variables**, add:

| Variable | Value |
|----------|--------|
| `RESEND_API_KEY` | Your Resend API key (e.g. `re_xxxxxxxx`) |
| `RESEND_FROM_EMAIL` | (Optional) e.g. `Nitya Dharma <onboarding@resend.dev>` or `Nitya Dharma <noreply@yourdomain.com>` after domain verification. If not set, the app uses `Nitya Dharma <onboarding@resend.dev>`. |

You do **not** need `EMAIL_HOST`, `EMAIL_HOST_USER`, or `EMAIL_HOST_PASSWORD` when using Resend. The app will use the Resend backend whenever `RESEND_API_KEY` is set.

---

## 3. Redeploy

Save the variables. Railway will redeploy. After deploy, trigger a **resend verification** or **Pandit registration** and check the recipient inbox (and spam).

---

## 4. Verify

- **Railway logs:** Look for no "Network is unreachable" and no Resend API errors.
- **Resend dashboard:** In Resend → **Emails**, you should see sent emails and their status.

---

## Summary

| Problem | Solution |
|--------|----------|
| `OSError: [Errno 101] Network is unreachable` to Gmail SMTP | Railway blocks SMTP. Use Resend (HTTPS). |
| Set on Railway | `RESEND_API_KEY` (required), optionally `RESEND_FROM_EMAIL` |
| Sandbox | Send only to your Resend account email until you verify a domain. |
| Production | Verify your domain in Resend and set `RESEND_FROM_EMAIL` to e.g. `noreply@yourdomain.com`. |
