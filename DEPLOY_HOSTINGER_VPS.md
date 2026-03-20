# Deploy Nitya Dharma on Hostinger KVM2 VPS

This guide prepares the Django project for **Hostinger KVM2** (2 vCPU, 8 GB RAM, 100 GB NVMe, 8 TB bandwidth). Gunicorn, logging, and Nginx are tuned for this plan.

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

---

## 4. Environment variables

Copy the example env file and edit with your values (no secrets in code):

```bash
cp .env.example .env
nano .env
```

Set at least:

- `SECRET_KEY` (long random string)
- `DEBUG=False`
- `ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com`
- `SITE_URL=https://yourdomain.com`
- `DATABASE_NAME=nityadharma_db`
- `DATABASE_USER=nityadharma_user`
- `DATABASE_PASSWORD=...`
- `DATABASE_HOST=localhost`
- `DATABASE_PORT=3306`
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`

---

## 5. Migrations and static files

```bash
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=nityadharma.settings.prod
python manage.py migrate
python manage.py collectstatic --noinput
```

Ensure `logs/` exists (prod settings create it automatically; if not):

```bash
mkdir -p logs
```

---

## 6. Test Gunicorn

```bash
export DJANGO_SETTINGS_MODULE=nityadharma.settings.prod
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

To load env from `.env` (recommended), uncomment and set in the service file:

```ini
EnvironmentFile=/var/www/nityadharma/.env
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
```

---

## 8. Nginx reverse proxy

Copy and enable the Nginx config (replace `yourdomain.com` with your domain):

```bash
sudo cp deployment/nginx_hostinger.conf /etc/nginx/sites-available/nityadharma
sudo sed -i 's/yourdomain.com/YOUR_ACTUAL_DOMAIN/g' /etc/nginx/sites-available/nityadharma
sudo ln -s /etc/nginx/sites-available/nityadharma /etc/nginx/sites-enabled/
# Remove default site if it conflicts:
# sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

Ensure Nginx can read static and media:

```bash
sudo chown -R www-data:www-data /var/www/nityadharma/staticfiles /var/www/nityadharma/media
# If you run gunicorn as your user, you may use the same user for static/media and adjust service User= accordingly
```

---

## 9. SSL with Let’s Encrypt (Certbot)

Install Certbot and get a certificate:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

Follow the prompts. Certbot will adjust Nginx for HTTPS. To redirect HTTP to HTTPS, ensure in Django prod settings you have:

- `SECURE_SSL_REDIRECT = True` (default in prod)
- Nginx already handles SSL; Django sees `X-Forwarded-Proto` and redirects if needed.

Renewal (automatic via systemd timer):

```bash
sudo certbot renew --dry-run
```

---

## 10. Security checklist

- **Secrets:** All credentials in `.env` or systemd `EnvironmentFile`; never in code.
- **DEBUG:** `DEBUG=False` in production (enforced in `nityadharma.settings.prod`).
- **HTTPS:** Certbot + Nginx; cookies and redirects are secure in prod.
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
- **Logging:** Rotating files under `logs/` (10 MB × 5 backups for `django.log`), sized for 8 GB RAM.
- **Static/Media:** Served by Nginx from `staticfiles/` and `media/` on NVMe; WhiteNoise still available if needed.
- **Database:** MySQL via `DATABASE_*` (or `DB_*`) env vars; no credentials in code.
- **Email:** SMTP via `EMAIL_*` env vars; no credentials in code.

After deployment, run `git status` and `git diff` before committing any changes; never commit `.env` or secrets.
