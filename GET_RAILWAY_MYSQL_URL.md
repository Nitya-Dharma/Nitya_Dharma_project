# How to Get Railway MySQL URL (Step-by-Step in Detail)

You need this URL to connect from your PC to Railway’s MySQL (e.g. for `loaddata`).  
Format: **mysql://&lt;username&gt;:&lt;password&gt;@&lt;host&gt;/&lt;database&gt;**  
(Use &lt;host&gt;:&lt;port&gt; when connecting via TCP Proxy, e.g. `proxy.rlwy.net:15140`. Never commit real URLs or passwords to Git.)

---

## Part 1: Open your project and MySQL service

1. Open your browser and go to **https://railway.app**.
2. Log in if needed.
3. Click your **project** (the one where your Nitya Dharma app and MySQL live).
4. On the project page you’ll see at least two services, e.g.:
   - **web** (your Django app from GitHub)
   - **MySQL** (the database)
5. Click the **MySQL** service (the database icon/name).  
   Do **not** click the web service.  
   The MySQL service view will open (tabs like Variables, Settings, Deployments, etc.).

---

## Part 2: Get user, password, and database name (Variables)

1. In the MySQL service, click the **Variables** tab (or **Settings** → **Variables**).
2. You’ll see a list of variables. Find and note these **exact** values (you can click to copy if Railway allows):

   | Variable name   | What to note              | Example value        |
   |-----------------|---------------------------|----------------------|
   | **MYSQLUSER**   | MySQL username            | `root`               |
   | **MYSQLPASSWORD** | MySQL password         | `abc123xyz` or `My@Pass#1` |
   | **MYSQLDATABASE** | Database name          | `railway`            |

3. Write them down in a temporary note (e.g. Notepad):
   - User: `_________`
   - Password: `_________`
   - Database: `_________`

   Keep this window/tab open; you’ll need these again when building the URL.

---

## Part 3: Get TCP Proxy host and port (Networking)

Railway’s MySQL is inside their network. To connect from **your PC**, you must use the **TCP Proxy**, which gives a public host and port.

1. Still in the **MySQL** service, open **Settings** (or the **Networking** / **Public Networking** section).
2. Find the **TCP Proxy** (or **Public Networking**) section.
3. If TCP Proxy is **disabled**, turn it **on** (toggle or “Enable”).
4. Once it’s on, Railway shows something like:
   - **Host** (or “Proxy host” / “Public host”): e.g. `shuttle.proxy.rlwy.net` or `monorail.proxy.rlwy.net`
   - **Port** (or “Proxy port” / “Public port”): a number, e.g. `15140` or `12345`
5. Note these two values:
   - TCP host: `_________________________`
   - TCP port: `_____`

   Example: host = `shuttle.proxy.rlwy.net`, port = `15140`.

---

## Part 4: Build the URL

The URL has this form:

```text
mysql://<username>:<password>@<host>/<database>
```

**Step A – Write it with your real values (password as-is first):**

- Replace **&lt;username&gt;** with the value of `MYSQLUSER`.
- Replace **&lt;password&gt;** with the value of `MYSQLPASSWORD` (copy exactly).
- Replace **&lt;host&gt;** with the TCP Proxy host and port (e.g. `proxy.rlwy.net:15140`).
- Replace **&lt;database&gt;** with the value of `MYSQLDATABASE`.

Example format only (do not use real credentials in any file):

```text
mysql://<username>:<password>@<host>/<database>
```

**Step B – URL-encode the password (important):**

The password goes in the middle of the URL. If it contains special characters, the URL can break or be interpreted wrongly. So we **encode** those characters.

Replace each special character in the **password only** with the value from this table:

| Character | Replace with |
|-----------|----------------|
| `@`       | `%40`         |
| `#`       | `%23`         |
| `%`       | `%25`         |
| `&`       | `%26`         |
| `=`       | `%3D`         |
| `?`       | `%3F`         |
| `+`       | `%2B`         |
| space     | `%20`         |
| `!`       | `%21`         |
| `$`       | `%24`         |
| `'`       | `%27`         |
| `(`       | `%28`         |
| `)`       | `%29`         |
| `*`       | `%2A`         |
| `,`       | `%2C`         |
| `/`       | `%2F`         |
| `:`       | `%3A`         |
| `;`       | `%3B`         |
| `<`       | `%3C`         |
| `>`       | `%3E`         |
| `[`       | `%5B`         |
| `]`       | `%5D`         |

**Example 1 – Password with `@`:**  
In the URL, encode `@` as `%40`: e.g. `MyPass@123` → `MyPass%40123`.

**Example 2 – Password with `#`:**  
Encode `#` as `%23`: e.g. `Secret#99` → `Secret%2399`.

**Example 3 – No special characters:**  
No encoding needed.

**Step C – Final check:**

- No spaces in the URL.
- Format is exactly: `mysql://<username>:<password>@<host>/<database>` (with password URL-encoded if it has special characters; &lt;host&gt; can include `:port`).
- The only `@` in the URL should be the one **between** the password and the host (the one that was already there; do not add an extra `@` from the password without encoding it).

Your final line is your **Railway MySQL URL**. Use it only in the next step (e.g. `MYSQL_URL` or `DATABASE_URL`) and do not commit it or share it.

---

## Part 5: Use the URL in PowerShell (for loaddata)

When you run loaddata, you’ll set the URL as an environment variable. In PowerShell, put your **full** URL inside double quotes:

```powershell
$env:MYSQL_URL="mysql://<username>:<password>@<host>/<database>"
```

Replace the entire URL with the one you built. If the URL is correct, the next command will connect to Railway’s MySQL:

```powershell
$env:DJANGO_SETTINGS_MODULE="nityadharma.settings.prod"
python manage.py check_db_connection
```

You should see the TCP proxy host and “Connected to Railway database.” Then you can run:

```powershell
python manage.py loaddata data_export.json
```

---

## Quick checklist

- [ ] Opened Railway → project → **MySQL** service (not web).
- [ ] From **Variables**: noted **MYSQLUSER**, **MYSQLPASSWORD**, **MYSQLDATABASE**.
- [ ] From **Settings / Networking**: turned on **TCP Proxy**, noted **host** and **port**.
- [ ] Built: `mysql://<username>:<password>@<host>/<database>`.
- [ ] URL-encoded any special characters in the **password** (e.g. `@` → `%40`).
- [ ] Used this URL only in `$env:MYSQL_URL="..."` and did not commit it.
