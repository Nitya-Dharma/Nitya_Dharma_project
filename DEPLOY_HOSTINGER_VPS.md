# Deploy Nitya Dharma on Hostinger KVM2 VPS

This guide is the **primary** production path for **Hostinger KVM2** (2 vCPU, 8 GB RAM, 100 GB NVMe, 8 TB bandwidth): bare-metal Nginx → Gunicorn (systemd) → Django `nityadharma.settings.prod` → MySQL on localhost.

**Not covered by this guide (separate paths):**

- **Docker Compose** — additive stack; see `docker-compose.yml` / `.env.example` (Batch 1 defaults Compose to prod settings).
- **Procfile / PaaS** (Railway, etc.) — uses `gunicorn.conf.py`; set `DJANGO_SETTINGS_MODULE` on the platform. Do not mix with this VPS procedure.

Gunicorn, logging, and Nginx below are tuned for the Hostinger KVM2 plan.

---

## 1. Server setup

SSH into your VPS and update the system:

```bash
sudo apt update && sudo apt upgrade -y
```

Install Python, Nginx, MySQL, and Git:

```bash
sudo apt install -y python3-pip python3-venv python3-dev nginx mysql-server git build-essential libmysqlclient-dev pkg-config
```

---

## 2. MySQL

Create a database and user:

```bash
sudo mysql -e "CREATE DATABASE nityadharma_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sudo mysql -e "CREATE USER 'nityadharma_user'@'localhost' IDENTIFIED BY 'YOUR_STRONG_PASSWORD';"
sudo mysql -e "GRANT ALL PRIVILEGES ON nityadharma_db.* TO 'nityadharma_user'@'localhost';"
sudo mysql -e "FLUSH PRIVILEGES;"
```

Use your own strong password. Do not commit it. Put the same value in `.env` as `DATABASE_PASSWORD`.

---

## 3. Project directory and virtual environment

```bash
sudo mkdir -p /var/www/nityadharma
sudo chown $USER:$USER /var/www/nityadharma
cd /var/www/nityadharma
git clone https://github.com/YOUR_ORG/nityadharma.git .
# Or upload via SFTP / rsync
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Ownership for systemd (`User=www-data`)

`deployment/gunicorn.service` runs Gunicorn as **`www-data`**. After install/setup as your SSH user, grant that account access (adjust only what is needed; do not invent a new service user):

```bash
# Readable app + venv for the service user
sudo chown -R www-data:www-data /var/www/nityadharma
# Or keep deployer ownership and use group/ACL; minimum: www-data must read code, venv, .env and write logs/ + media/
```

If you prefer to keep the tree owned by your deploy user, you must still ensure `www-data` can execute the venv Gunicorn binary and read `.env`. Changing `User=` in the unit is a separate ops decision — this repository’s service file uses `www-data`.

---

## 4. Environment variables

Copy the example env file and edit with your values (no secrets in code):

```bash
cp .env.example .env
nano .env
```

Never commit `.env`. systemd loads it via `EnvironmentFile=/var/www/nityadharma/.env` in `deployment/gunicorn.service`.

Set at least:

- `SECRET_KEY` (long random string) — **required** by prod settings
- `DEBUG=False` (prod also hardcodes `DEBUG = False`)
- `SITE_URL=https://yourdomain.com`
- `DATABASE_NAME=nityadharma_db`
- `DATABASE_USER=nityadharma_user`
- `DATABASE_PASSWORD=...` (same as MySQL user password)
- `DATABASE_HOST=localhost`
- `DATABASE_PORT=3306`
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`
- `SECURE_SSL_REDIRECT=True` after TLS is live (default in prod is True)

### Hosts / CSRF (current prod behavior — important)

`nityadharma.settings.prod` currently **hardcodes**:

- `ALLOWED_HOSTS` → `nityadharma.com`, `www.nityadharma.com`
- `CSRF_TRUSTED_ORIGINS` → `https://nityadharma.com`, `https://www.nityadharma.com`

Setting `ALLOWED_HOSTS=...` in `.env` does **not** change those values while using `nityadharma.settings.prod`.
`.env.example` may still show host placeholders for other paths or future work.

**Future separate batch (not done here):** make `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` environment-driven if multi-domain VPS deploys need it.

### Logging directory

Prod settings read `LOG_DIR` from the environment (default in code is `/logs`, which suits Docker).
For Hostinger, the systemd unit sets:

```ini
Environment="LOG_DIR=/var/www/nityadharma/logs"
```

Create the directory and ensure `www-data` can write it:

```bash
mkdir -p /var/www/nityadharma/logs
sudo chown www-data:www-data /var/www/nityadharma/logs
```

Do not change `prod.py` for Hostinger logging; set `LOG_DIR` via systemd (already in the unit) or `.env` if you override it.

### Celery

This Hostinger guide does **not** install or manage Celery. There is no `celery.service` in `deployment/`. Async workers are part of the **Docker Compose** path unless you add a separate ops unit later.

---

## 5. Migrations and static files

```bash
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=nityadharma.settings.prod
export LOG_DIR=/var/www/nityadharma/logs
python manage.py migrate
python manage.py collectstatic --noinput
```

Ensure logs exist (see §4):

```bash
mkdir -p /var/www/nityadharma/logs
```

---

## 6. Test Gunicorn

```bash
export DJANGO_SETTINGS_MODULE=nityadharma.settings.prod
export LOG_DIR=/var/www/nityadharma/logs
gunicorn nityadharma.wsgi:application --config gunicorn_config.py
```

In another terminal: `curl http://127.0.0.1:8000/`. Then stop Gunicorn (Ctrl+C).

---

## 7. systemd service for Gunicorn

Use the project’s service file (paths assume app at `/var/www/nityadharma`):

```bash
sudo cp deployment/gunicorn.service /etc/systemd/system/
# If your app lives elsewhere, edit paths in the service file:
# sudo nano /etc/systemd/system/gunicorn.service
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
sudo systemctl start gunicorn
sudo systemctl status gunicorn
```

The unit already:

- sets `DJANGO_SETTINGS_MODULE=nityadharma.settings.prod`
- sets `LOG_DIR=/var/www/nityadharma/logs`
- loads `EnvironmentFile=/var/www/nityadharma/.env`
- runs as `User=www-data` / `Group=www-data`
- starts: `gunicorn nityadharma.wsgi:application --config gunicorn_config.py`

If the service fails on start, confirm `.env` exists at `/var/www/nityadharma/.env` and is readable by `www-data`.

After editing `.env` or the unit:

```bash
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
```

---

## 8. Nginx reverse proxy

The repository ships an **HTTP (port 80) template** for initial setup. HTTPS is **not** active in the template until you obtain certificates on the VPS.

Copy and enable the Nginx config (replace `yourdomain.com` with your domain **on the server**, not by committing secrets/domains into git):

```bash
sudo cp deployment/nginx_hostinger.conf /etc/nginx/sites-available/nityadharma
sudo sed -i 's/yourdomain.com/YOUR_ACTUAL_DOMAIN/g' /etc/nginx/sites-available/nityadharma
sudo ln -s /etc/nginx/sites-available/nityadharma /etc/nginx/sites-enabled/
# Remove default site if it conflicts:
# sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

Ensure Nginx (`www-data`) can read static and media:

```bash
sudo chown -R www-data:www-data /var/www/nityadharma/staticfiles /var/www/nityadharma/media
```

Upstream is `127.0.0.1:8000` (Gunicorn). Proxy sets `X-Forwarded-Proto $scheme` for Django `SECURE_PROXY_SSL_HEADER`.

---

## 9. SSL with Let’s Encrypt (Certbot) — VPS operations step

**Repository state:** `deployment/nginx_hostinger.conf` starts as HTTP-only. The HTTPS server block in that file is a **commented example**. Shipping the repo does **not** mean TLS is live.

On the VPS, after DNS points to the server:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

Typical sequence:

1. HTTP template works for initial reachability / ACME challenges.
2. Point DNS A/AAAA records at the VPS.
3. Run Certbot; it obtains certificates and adjusts Nginx for HTTPS.
4. Prefer Certbot-managed HTTPS over manually uncommenting the sample block with incomplete paths.
5. After TLS is actually active, enable HTTP → HTTPS redirect (Certbot option and/or the commented `return 301` in the HTTP server).
6. Keep Django `SECURE_SSL_REDIRECT=True` (prod default) so redirects/cookies align once the proxy sends `X-Forwarded-Proto: https`.

Renewal check:

```bash
sudo certbot renew --dry-run
```

Do not commit real certificate files or private keys into the repository.

---

## 10. Security checklist

- **Secrets:** In `.env` loaded by systemd `EnvironmentFile`; never in git.
- **DEBUG:** `False` in `nityadharma.settings.prod`.
- **Hosts:** Currently hardcoded in prod settings (see §4); deploy on `nityadharma.com` / `www` or plan a future env-driven hosts batch.
- **HTTPS:** Only after Certbot on the VPS; do not treat the repo template as TLS-complete.
- **Firewall:** `sudo ufw allow 22 && sudo ufw allow 80 && sudo ufw allow 443 && sudo ufw enable`.

---

## 11. Useful commands

| Task              | Command |
|-------------------|--------|
| Gunicorn status   | `sudo systemctl status gunicorn` |
| Gunicorn logs     | `journalctl -u gunicorn -f` |
| Django app logs  | `tail -f /var/www/nityadharma/logs/django.log` |
| Nginx test        | `sudo nginx -t` |
| Nginx reload      | `sudo systemctl reload nginx` |
| Restart app       | `sudo systemctl restart gunicorn` |

---

## 12. VPS specs (KVM2)

Configurations used for this plan:

- **Gunicorn:** 3 workers, sync, timeout 120s, bind `127.0.0.1:8000` (see `gunicorn_config.py`).
- **Logging:** `LOG_DIR=/var/www/nityadharma/logs` via systemd; rotating files (10 MB × 5 backups).
- **Static/Media:** Served by Nginx from `staticfiles/` and `media/` on NVMe; WhiteNoise still available if needed.
- **Database:** MySQL via `DATABASE_*` (or `DB_*`) env vars; no credentials in code.
- **Email:** SMTP via `EMAIL_*` env vars; no credentials in code.
- **Celery:** Not managed by this Hostinger systemd path.

After deployment, run `git status` and `git diff` before committing any changes; never commit `.env` or secrets.
