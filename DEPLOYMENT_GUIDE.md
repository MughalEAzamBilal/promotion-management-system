# Teacher Promotion Portal - Production Deployment Guide
**School Education Department (SED), Government of the Punjab**

This guide provides instructions for deploying the **Teacher Promotion Portal** to a live production server.

---

## 1. Pre-Deployment Preparation & Architecture Overview

* **Framework**: Python 3.10+ / Flask 3.0+
* **ORM**: SQLAlchemy 2.0+
* **Database Options**:
  * **PostgreSQL 14+** (Recommended for multi-district concurrent access)
  * **MySQL / MariaDB 10.5+** (Supported via `mysql+pymysql://`)
  * **SQLite 3** (Default, self-contained file in `instance/teacher_promotion.db`)
* **WSGI Production Servers**:
  * **Gunicorn** (Linux VPS / Cloud PaaS)
  * **Passenger WSGI** (cPanel / CloudLinux)
  * **Waitress** (Windows Server)

---

## 2. Environment Variables Configuration

Copy `.env.example` to `.env` in the application root directory:

```bash
cp .env.example .env
```

Generate a secure random secret key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Configure `.env`:
```ini
FLASK_ENV=production
FLASK_DEBUG=0
SECRET_KEY=your_generated_cryptographic_secret_key_here

# Database Configuration:
# PostgreSQL:
# DATABASE_URL=postgresql://db_user:db_password@localhost:5432/sed_promotion_db
# SQLite:
DATABASE_URL=sqlite:///instance/teacher_promotion.db

# Statutory Session Timeout (10 minutes)
SESSION_TIMEOUT_MINUTES=10

HOST=0.0.0.0
PORT=5000
```

---

## 3. Deployment Options

### Option A: Linux VPS (Ubuntu / Debian + Nginx + Gunicorn + Systemd)

#### Step 1: Install System Dependencies
```bash
sudo apt update && sudo apt install -y python3-pip python3-venv nginx git
```

#### Step 2: Clone / Upload Project to `/var/www/promotion_portal`
```bash
sudo mkdir -p /var/www/promotion_portal
sudo chown -R $USER:$USER /var/www/promotion_portal
# Upload files or clone repository into /var/www/promotion_portal
cd /var/www/promotion_portal
```

#### Step 3: Setup Virtual Environment & Install Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 4: Initialize & Seed the Database
```bash
python init_db.py
```

#### Step 5: Configure Systemd Service
Create `/etc/systemd/system/promotion_portal.service`:
```ini
[Unit]
Description=Punjab SED Teacher Promotion Portal WSGI Service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/promotion_portal
Environment="PATH=/var/www/promotion_portal/venv/bin"
EnvironmentFile=/var/www/promotion_portal/.env
ExecStart=/var/www/promotion_portal/venv/bin/gunicorn --workers 4 --threads 2 --bind 127.0.0.1:5000 wsgi:app

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo chown -R www-data:www-data /var/www/promotion_portal
sudo chmod -R 775 /var/www/promotion_portal/uploads /var/www/promotion_portal/backups /var/www/promotion_portal/instance
sudo systemctl daemon-reload
sudo systemctl enable promotion_portal
sudo systemctl start promotion_portal
sudo systemctl status promotion_portal
```

#### Step 6: Configure Nginx Reverse Proxy & SSL
Create `/etc/nginx/sites-available/promotion_portal`:
```nginx
server {
    listen 80;
    server_name your-portal-domain.gov.pk;

    client_max_body_size 35M;

    location /static/ {
        alias /var/www/promotion_portal/app/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 180s;
        proxy_connect_timeout 60s;
    }
}
```

Enable site & get SSL Certificate (Let's Encrypt):
```bash
sudo ln -s /etc/nginx/sites-available/promotion_portal /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Install free Let's Encrypt SSL
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-portal-domain.gov.pk
```

---

### Option B: cPanel / Cloud Hosting ("Setup Python App" via Passenger)

1. Log into your **cPanel** control panel.
2. In the **Software** section, click **Setup Python App**.
3. Click **Create Application**:
   * **Python version**: Select `3.10` or `3.11`.
   * **Application root**: `promotion_portal` (or your folder name).
   * **Application URL**: `your-domain.gov.pk` or subdomain.
   * **Application startup file**: `passenger_wsgi.py` (or `wsgi.py`).
   * **Application Entry point**: `app` (or `application`).
4. Click **Create**.
5. Upload all project files into the Application Root directory using cPanel File Manager or FTP.
6. Connect via SSH or use cPanel Terminal, activate the virtual environment path shown at the top of the Setup Python App page, and run:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   python init_db.py
   ```
7. Configure `passenger_wsgi.py`:
   ```python
   import sys, os
   sys.path.insert(0, os.path.dirname(__file__))
   from wsgi import app as application
   ```
8. In the cPanel Setup Python App page, click **Restart** to activate the live site.

---

### Option C: Cloud PaaS (Render / Railway / Heroku)

The repository includes a ready-to-use [`Procfile`](file:///c:/Users/Mughal%20e%20Azam%20Bilal/Downloads/WebProjects/PromotionManagementSystem/Procfile):
```
web: gunicorn wsgi:app --workers 4 --threads 2 --timeout 120 --log-file -
```

1. **Connect Repository**: Link your Git repository on [Render.com](https://render.com) or [Railway.app](https://railway.app).
2. **Build Command**: `pip install -r requirements.txt && python init_db.py`
3. **Start Command**: `gunicorn wsgi:app`
4. **Environment Variables**:
   * `SECRET_KEY`: Set to your cryptographic key.
   * `DATABASE_URL`: Add your PostgreSQL database connection string.
   * `FLASK_ENV`: `production`

---

### Option D: PythonAnywhere

1. Open your **PythonAnywhere Web Tab**.
2. Add a new web app selecting **Manual configuration** with **Python 3.10+**.
3. In the virtualenv section, set the path to your created virtual environment.
4. In the WSGI configuration file (`/var/www/yourusername_pythonanywhere_com_wsgi.py`), replace contents with:
   ```python
   import sys, os
   path = '/home/yourusername/promotion_portal'
   if path not in sys.path:
       sys.path.append(path)
   
   from wsgi import app as application
   ```
5. Run Bash console, run `pip install -r requirements.txt` and `python init_db.py`.
6. Click **Reload yourusername.pythonanywhere.com**.

---

### Option E: Windows Server (Waitress WSGI / IIS)

1. Open PowerShell as Administrator on the Windows Server.
2. In the application directory:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python init_db.py
   ```
3. Run using Waitress production server:
   ```powershell
   waitress-serve --listen=0.0.0.0:5000 wsgi:app
   ```
4. Optional: Configure **IIS (Internet Information Services)** with `HttpPlatformHandler` or `wfastcgi` reverse proxying to `localhost:5000`.

---

## 4. Production Security Checklist

- [ ] **Cryptographic Secret Key**: Ensure `SECRET_KEY` in `.env` is at least 32 characters long and random.
- [ ] **HTTPS Enforced**: Ensure SSL/TLS certificate is active on Nginx or Cloudflare.
- [ ] **File Permissions**: Ensure `uploads/`, `backups/`, and `instance/` have write permissions for the web server user (`chmod 775` or `www-data`).
- [ ] **Database Backups**: Schedule automated daily backups via cron:
  ```bash
  0 2 * * * cd /var/www/promotion_portal && /var/www/promotion_portal/venv/bin/python -c "import shutil, datetime; shutil.copy('instance/teacher_promotion.db', f'backups/db_{datetime.date.today()}.db')"
  ```
- [ ] **Inactivity Timeout**: Verified at 10 minutes (`SESSION_TIMEOUT_MINUTES=10`).
- [ ] **Admin Passwords**: Ensure default credentials (`Admin@123`, `SuperAdmin@123`) are rotated immediately upon first live administrative login.
