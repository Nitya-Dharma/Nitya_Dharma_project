# Load Local DB Data to Railway – Step-by-Step

Follow these steps in order. Use the **public** MySQL URL (TCP Proxy) only on your PC; do not commit or share it.

---

## Step 1: Export data from your local database

Do this first so you have a file to load.

1. Open **PowerShell** (or Windows Terminal).
2. Go to your project folder:
   ```powershell
   cd "c:\Users\KABDE SHRUTHI\OneDrive\Desktop\Nitya Dharma"
   ```
3. Activate your virtual environment (if you use one):
   ```powershell
   venv\Scripts\activate
   ```
4. Make sure Django is using your **local** database (your normal `.env` or local MySQL). Do **not** set `MYSQL_URL` or `DATABASE_URL` yet.
5. Run the export command (excluding behavior_engine to avoid duplicate-key errors on Railway):
   ```powershell
   python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission -e sessions.Session -e admin.LogEntry -e behavior_engine -o data_export.json
   ```
6. Wait until it finishes. You should see a file **data_export.json** in your project folder.
7. Check that the file exists and is not empty:
   ```powershell
   dir data_export.json
   ```

---

## Step 2: Open PowerShell in your project folder (for the next steps)

1. Open **PowerShell** (or use the same window from Step 1).
2. Go to your project folder:
   ```powershell
   cd "c:\Users\KABDE SHRUTHI\OneDrive\Desktop\Nitya Dharma"
   ```
3. Activate virtual environment if you use one:
   ```powershell
   venv\Scripts\activate
   ```

---

## Step 3: Set the Railway MySQL URL (public TCP Proxy URL)

Use the **public** URL so your PC can connect to Railway’s MySQL. Do **not** use `mysql.railway.internal` here; that only works inside Railway.

1. Copy this line exactly, then paste it into PowerShell and press **Enter**:
   ```powershell
   $env:MYSQL_URL="mysql://root:gvAHfqlVjRUCdVipzduMNeWMgJmIwire@centerbeam.proxy.rlwy.net:13686/railway"
   ```
2. Nothing will be printed. The variable is now set for this terminal session only.

**Important:** This URL is only for running commands on your PC. Do not put this URL in Railway’s web service Variables; the web service must keep using the **internal** URL (`mysql.railway.internal:3306`).

---

## Step 4: Set Django to use production settings

1. In the **same** PowerShell window, run:
   ```powershell
   $env:DJANGO_SETTINGS_MODULE="nityadharma.settings.prod"
   ```
2. Press **Enter**. Again, nothing will be printed.

---

## Step 5: Check that you are connected to Railway’s database

Before loading data, confirm that Django is talking to Railway and not your local DB.

1. In the **same** PowerShell window, run:
   ```powershell
   python manage.py check_db_connection
   ```
2. You should see something like:
   - **DB host:** `centerbeam.proxy.rlwy.net` (or similar)
   - **DB name:** `railway`
   - **Connected to Railway database.**
3. If you see **localhost** or a local DB name, stop. The URL in Step 3 is wrong or not set; fix it and repeat from Step 3.

---

## Step 6: Load the data into Railway’s database

1. In the **same** PowerShell window, run:
   ```powershell
   python manage.py loaddata data_export.json
   ```
2. Wait until it finishes. You should see lines like **Installed 1234 object(s)** (the number will vary).
3. If you see errors (e.g. duplicate key), some data may already exist on Railway. You can note the error and continue, or fix and run again. A successful run means the data from the file is now in Railway’s MySQL.

---

## Step 7: Clear the environment variables (so you don’t accidentally use Railway DB later)

1. In the **same** PowerShell window, run these three lines one by one:
   ```powershell
   Remove-Item Env:MYSQL_URL -ErrorAction SilentlyContinue
   Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
   $env:DJANGO_SETTINGS_MODULE=""
   ```
2. After this, your next commands in this window will use your normal (local) settings again.  
   Or you can simply **close** the window and open a new one for normal work.

---

## Step 8: Verify on the Railway website

1. Open your Railway app in the browser (e.g. **https://web-production-7256f4.up.railway.app**).
2. Log in with a user that existed in your local database (same email and password as locally).
3. Check that the data you expect is there (e.g. poojas, pages, master data).  
   If you see it, the load was successful.

---

## Step 9: Delete the export file (recommended)

The file contains a copy of your database and may include sensitive data. Do not commit it.

1. In PowerShell (in your project folder), run:
   ```powershell
   del data_export.json
   ```
2. Confirm the file is gone (optional):
   ```powershell
   dir data_export.json
   ```
   You should see “cannot find file” or similar.  
   The file is already in `.gitignore`, so it would not be committed even if you left it; deleting it is an extra safety step.

---

## Reminder: Two different URLs

| Where you use it | URL to use |
|------------------|------------|
| **Railway web service → Variables (MYSQL_URL)** | Internal: `mysql://root:...@mysql.railway.internal:3306/railway` — so the **deployed app** on Railway can connect. |
| **Your PC (only when running loaddata)** | Public: `mysql://root:...@centerbeam.proxy.rlwy.net:13686/railway` — so **your computer** can connect. |

- **Keep** the internal URL in Railway’s web service.
- **Use** the public URL only in PowerShell on your PC (Steps 3–6), and **do not commit or share** it.

---

## Quick checklist

- [ ] Step 1: Exported local data to **data_export.json**
- [ ] Step 2: Opened PowerShell in project folder, venv activated
- [ ] Step 3: Set **MYSQL_URL** to the **public** URL (centerbeam.proxy.rlwy.net:13686)
- [ ] Step 4: Set **DJANGO_SETTINGS_MODULE** to **nityadharma.settings.prod**
- [ ] Step 5: Ran **check_db_connection** and saw Railway’s host/DB name
- [ ] Step 6: Ran **loaddata data_export.json** and saw “Installed … object(s)”
- [ ] Step 7: Cleared **MYSQL_URL** and **DJANGO_SETTINGS_MODULE** (or closed the terminal)
- [ ] Step 8: Checked the Railway site and saw your data
- [ ] Step 9: Deleted **data_export.json**

You’re done. Your local data is now on Railway.
