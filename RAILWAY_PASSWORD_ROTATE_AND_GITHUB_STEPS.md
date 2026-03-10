# Step-by-Step: Rotate Railway MySQL Password & Fix GitHub

Do these steps **in order**. You will: (1) change the MySQL password on Railway, (2) make sure your app still connects, (3) commit and push the doc fix to GitHub.

---

## Part A: Rotate the MySQL password on Railway

### Step A1: Open your Railway project

1. Go to **https://railway.app** and log in.
2. Click your **project** (the one with your Nitya Dharma app and MySQL).
3. You should see at least two services (e.g. **web**, **MySQL**).

---

### Step A2: Open the MySQL service (not the web service)

1. Click the **MySQL** service (the database).
2. You should see tabs like **Variables**, **Settings**, **Deployments**, etc.

---

### Step A3: Find how Railway gives you the MySQL password

Railway usually does **one** of these:

- **Option 1 – You see variables:** In the **Variables** tab you see things like `MYSQLUSER`, `MYSQLPASSWORD`, `MYSQLDATABASE`, and sometimes **`MYSQL_URL`** (a full connection string).  
  → The password is inside **MYSQLPASSWORD** (or inside **MYSQL_URL** if that’s the only thing you see).

- **Option 2 – You don’t see the password:** Some Railway MySQL templates don’t show the raw password; they only show **MYSQL_URL**. In that case you **regenerate** the URL/password from Settings (see Step A5).

**What you need to do:**  
- If you **can** edit **MYSQLPASSWORD**: you will set a **new password** (Step A4).  
- If you **cannot** see or edit **MYSQLPASSWORD**: you will use **Settings** to **reset/regenerate** the MySQL root password (Step A5).

---

### Step A4: Change the password (when you CAN edit MYSQLPASSWORD)

1. In the **MySQL** service, open the **Variables** tab.
2. Find **MYSQLPASSWORD**.
3. Click to **edit** it (pencil icon or “Edit”).
4. Set a **new strong password** (e.g. long random string, no spaces). Save.
5. Railway may show **MYSQL_URL** as well. If **MYSQL_URL** is a single variable that contains the full URL (e.g. `mysql://root:OLD_PASS@host:port/railway`), it is often **auto-generated** from MYSQLUSER, MYSQLPASSWORD, etc. So after you change **MYSQLPASSWORD**, **MYSQL_URL** might **update automatically**.  
   - If you see **MYSQL_URL** and it did **not** change, edit it and replace the **old password** in the URL with your **new password** (and URL-encode special characters: `@` → `%40`, `#` → `%23`, etc.).
6. **Note down the new password** in a safe place (e.g. password manager). You will need it only when running `loaddata` from your PC (and never put it in Git).

**Then go to Part B** to make sure the **web** service still has the right URL.

---

### Step A5: Reset/regenerate the password (when you CANNOT edit MYSQLPASSWORD)

1. In the **MySQL** service, open the **Settings** tab (or **Variables**).
2. Look for something like:
   - **“Reset root password”**, or  
   - **“Regenerate credentials”**, or  
   - **“Reset MySQL”** / **“Redeploy”** (which can issue a new password).
3. Use that to get a **new** password/URL.
4. After reset, open **Variables** again and **copy the new MYSQL_URL** (or note the new MYSQLPASSWORD if shown). You will use this in the **web** service and, when needed, on your PC for `loaddata`.

**Then go to Part B.**

---

## Part B: Update the Web service so the app still connects

Your **Django app** (web service) connects to MySQL using **MYSQL_URL**. That URL must contain the **new** password.

### Step B1: Open the Web service

1. In the same Railway project, click the **web** service (your Django app), not MySQL.

---

### Step B2: Check how MYSQL_URL is set on the Web service

Open the **Variables** tab of the **web** service.

- **If you see “Reference” or “Add reference”:**  
  MYSQL_URL is probably **referencing** the MySQL service. When you changed the password on the **MySQL** service (Part A), the **reference** usually picks up the new value automatically.  
  → You often **don’t need to change anything** on the web service. Redeploy the web service once if Railway didn’t auto-redeploy (Deployments → three dots → Redeploy).

- **If MYSQL_URL is a plain value** (a long string like `mysql://root:something@host:port/railway`):  
  You must **update that value** so the password in the URL is the **new** password you set in Part A.  
  1. Click **Edit** on **MYSQL_URL**.  
  2. Replace **only the password part** in the URL with your **new** password.  
     - Format: `mysql://USER:PASSWORD@HOST:PORT/DATABASE`  
     - If the new password has special characters, URL-encode them (`@` → `%40`, `#` → `%23`, etc.).  
  3. Save.  
  4. Railway will redeploy the web service; wait until the deployment succeeds.

---

### Step B3: Confirm the app works

1. Open your app in the browser (e.g. `https://web-production-7256f4.up.railway.app` or your Railway URL).
2. Log in and use the site. If the app loads and can read/write data, the **web** service is using the new password correctly.

---

## Part C: What to change on your PC (only when you run loaddata)

You do **not** change anything in the repo or in a file. You only use the new URL **in the terminal**, and only when you run `loaddata`.

- When you need to run `loaddata` again:
  1. Build the URL with the **new** password:  
     `mysql://root:NEW_PASSWORD@TCP_PROXY_HOST:PORT/railway`  
     (URL-encode special characters in the password.)
  2. In **PowerShell**, in the **same** session where you will run Django commands, run **only once**:  
     `$env:MYSQL_URL="mysql://root:NEW_ENCODED_PASSWORD@TCP_HOST:PORT/railway"`  
     (Replace the whole URL with your real one.)
  3. Run your commands, e.g.:  
     `$env:DJANGO_SETTINGS_MODULE="nityadharma.settings.prod"`  
     `python manage.py check_db_connection`  
     `python manage.py loaddata data_export.json`
  4. When done, clear the variable:  
     `Remove-Item Env:MYSQL_URL -ErrorAction SilentlyContinue`

- **Do not** put the real URL or password in any file (no `.env` for production DB URL, no markdown, no code). Use it only in the terminal.

**Summary for PC:**  
- **Change:** The **value** you use when you set `$env:MYSQL_URL="..."` — it must be the **new** URL with the **new** password.  
- **Do not change:** Any file in the repo; no commit of the real URL or password.

---

## Part D: What to do on GitHub (commit and push the doc fix)

This removes the **current** file that contained the secret (we already replaced the real URL with placeholders in the doc). You only need to commit and push.

### Step D1: Open terminal in your project folder

1. Open **PowerShell** (or your terminal).
2. Go to your project:
   ```powershell
   cd "C:\Users\KABDE SHRUTHI\OneDrive\Desktop\Nitya Dharma"
   ```

---

### Step D2: Check status

Run:

```powershell
git status
```

You should see **LOAD_DATA_TO_RAILWAY_STEP_BY_STEP.md** as modified (and optionally other files). We only need to commit the doc fix for the secret.

---

### Step D3: Stage only the doc fix (and any other security-related edits)

Run:

```powershell
git add LOAD_DATA_TO_RAILWAY_STEP_BY_STEP.md
```

If you also want to add other already-fixed files (e.g. GET_RAILWAY_MYSQL_URL.md) that had no real secret, you can add them. Do **not** add `.env` or any file that contains a real MySQL URL or password.

---

### Step D4: Commit

Run:

```powershell
git commit -m "Security: remove exposed MySQL URL from doc, use placeholders"
```

---

### Step D5: Push to GitHub

Run:

```powershell
git push origin main
```

(If your default branch is `master`, use `git push origin master`.)

---

### What this changes on GitHub

- The **latest** version of **LOAD_DATA_TO_RAILWAY_STEP_BY_STEP.md** on GitHub will no longer contain the real MySQL URL; it will have placeholders only.
- **Old commits** will still contain the old URL in history. That’s why rotating the password (Part A) is required: the old password is then useless. Optionally you can later remove the secret from history (see Part E).

---

## Part E: (Optional) Remove the secret from Git history

Only do this **after** you have rotated the password (Part A) and updated the web service (Part B). Otherwise the app could break.

- **Why optional:** Once the password is rotated, the old password in old commits cannot be used to log in. So the main risk is already fixed.
- **Why you might do it:** To fully remove the secret from the repo history so scanners (e.g. GitGuardian) don’t keep flagging it.

This requires rewriting history and force-pushing. If others use the same repo, coordinate with them.

### Option 1: Using git filter-repo (recommended)

1. Install **git-filter-repo**: `pip install git-filter-repo`
2. Create a replacement file (e.g. `replacements.txt`) with one line:
   ```
   EXACT_LEAKED_URL_AS_IT_APPEARS_IN_HISTORY==>mysql://<username>:<password>@<host>/<database>
   ```
3. In your project folder run:
   ```powershell
   git filter-repo --replace-text replacements.txt --force
   ```
4. Then force-push:
   ```powershell
   git push origin main --force
   ```
   **Warning:** This rewrites history. Anyone else with the repo should re-clone or follow Git’s instructions to reset their local branch.

### Option 2: Using BFG Repo-Cleaner

1. Download BFG and use it to replace the secret string in history, then run `git reflog expire --expire=now --all && git gc --prune=now --aggressive` and force-push. (Exact commands depend on BFG version; we can spell them out if you choose this.)

### After rewriting history

- Everyone who has cloned the repo should re-clone or follow instructions to reset their local repo to the new history.
- GitGuardian may take some time to rescan; the incident may close once the secret is no longer in the repo.

---

## Quick checklist

- [ ] **A:** Rotated MySQL password on Railway (MySQL service → Variables or Settings).
- [ ] **B:** Web service still has correct MYSQL_URL (reference or updated value); app works in browser.
- [ ] **C:** On PC: use new URL only in terminal for `loaddata`; never put it in a file or commit.
- [ ] **D:** Committed and pushed the doc fix: `git add LOAD_DATA_TO_RAILWAY_STEP_BY_STEP.md`, `git commit`, `git push origin main`.
- [ ] **E (optional):** Removed secret from Git history and force-pushed; team re-synced to new history.

---

## Summary: what you change where

| Where | What to change |
|-------|-----------------|
| **Railway → MySQL service** | Set a **new** MySQL password (Variables or Settings reset). |
| **Railway → Web service** | Ensure **MYSQL_URL** uses the **new** password (by reference or by editing the variable). |
| **Your PC** | When running loaddata, set **$env:MYSQL_URL** to the **new** URL (new password) only in the terminal; never in a file. |
| **GitHub (repo)** | Commit and push the **doc fix** (placeholder URL in LOAD_DATA_TO_RAILWAY_STEP_BY_STEP.md). No real URL or password in any committed file. |
| **Git history (optional)** | Use git filter-repo or BFG to replace the old URL in all commits, then force-push. |
