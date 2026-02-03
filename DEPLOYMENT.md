# Production Deployment Guide

This guide covers deploying Grounded in a production environment without Docker containers.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Environment Configuration](#environment-configuration)
- [Database Setup](#database-setup)
- [Application Setup](#application-setup)
- [Security Hardening](#security-hardening)
- [Monitoring](#monitoring)
- [Systemd Service](#systemd-service)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements
- **OS**: Linux (Ubuntu 20.04+, Debian 11+, or RHEL 8+)
- **Python**: 3.11 or 3.12
- **PostgreSQL**: 15.x with pgvector extension
- **RAM**: Minimum 2GB, recommended 4GB+
- **Storage**: 10GB+ for application and logs
- **Network**: HTTPS/TLS termination (reverse proxy)

### Required Software
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    postgresql-15 \
    postgresql-contrib \
    postgresql-15-pgvector \
    nginx \
    supervisor

# RHEL/CentOS
sudo dnf install -y \
    python311 \
    python311-devel \
    postgresql15-server \
    postgresql15-contrib \
    nginx
```

---

## Environment Configuration

### 1. Create Production Environment File

Create `/etc/grounded/.env`:

```bash
sudo mkdir -p /etc/grounded
sudo nano /etc/grounded/.env
```

**Required Settings**:

```bash
# =============================================================================
# PRODUCTION ENVIRONMENT CONFIGURATION
# =============================================================================

# Environment (MUST be 'prod' for production)
ENV=prod

# =============================================================================
# Database
# =============================================================================
DATABASE_URL=postgresql://grounded:SECURE_PASSWORD@localhost:5432/grounded

# =============================================================================
# Security - CRITICAL
# =============================================================================
# Generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'
SECRET_KEY=YOUR_GENERATED_SECRET_KEY_HERE_MINIMUM_32_CHARACTERS

# CSRF Secret (auto-generated if not provided, but recommended to set explicitly)
CSRF_SECRET_KEY=YOUR_CSRF_SECRET_KEY_HERE

# Cookie Security (automatically enforced in prod)
COOKIE_SECURE=true
COOKIE_HTTPONLY=true
COOKIE_SAMESITE=lax

# =============================================================================
# Rate Limiting
# =============================================================================
RATE_LIMIT_ENABLED=true
RATE_LIMIT_AUTH_REQUESTS=5
RATE_LIMIT_AUTH_WINDOW=60
RATE_LIMIT_RAG_REQUESTS=20
RATE_LIMIT_RAG_WINDOW=60

# =============================================================================
# Logging
# =============================================================================
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/var/log/grounded/app.log

# =============================================================================
# OpenAI API
# =============================================================================
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-your-production-api-key
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_CHAT_TEMPERATURE=0.1

# =============================================================================
# RAG Configuration
# =============================================================================
RAG_TOP_K=5
RAG_SIMILARITY_THRESHOLD=0.7
RAG_MAX_CONTEXT_LENGTH=4000

# =============================================================================
# Admin - DO NOT SET IN PRODUCTION
# =============================================================================
# Create admin users through proper channels, not via env var
# ADMIN_PASSWORD=  # LEAVE EMPTY
```

### 2. Set Secure Permissions

```bash
sudo chown root:grounded /etc/grounded/.env
sudo chmod 640 /etc/grounded/.env
```

### 3. Generate Secrets

```bash
# Generate SECRET_KEY
python -c 'import secrets; print(f"SECRET_KEY={secrets.token_urlsafe(32)}")'

# Generate CSRF_SECRET_KEY
python -c 'import secrets; print(f"CSRF_SECRET_KEY={secrets.token_urlsafe(32)}")'
```

Add these to `/etc/grounded/.env`.

---

## Database Setup

### 1. Install PostgreSQL with pgvector

```bash
# Install PostgreSQL 15
sudo apt install -y postgresql-15 postgresql-contrib

# Install pgvector extension
sudo apt install -y postgresql-15-pgvector

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 2. Create Database and User

```bash
sudo -u postgres psql <<EOF
CREATE USER grounded WITH PASSWORD 'SECURE_PASSWORD_HERE';
CREATE DATABASE grounded OWNER grounded;
\c grounded
CREATE EXTENSION vector;
GRANT ALL PRIVILEGES ON DATABASE grounded TO grounded;
EOF
```

### 3. Configure PostgreSQL

Edit `/etc/postgresql/15/main/postgresql.conf`:

```ini
listen_addresses = 'localhost'  # Only local connections
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
```

Edit `/etc/postgresql/15/main/pg_hba.conf`:

```
# Only allow local connections with password
local   all             grounded                              scram-sha-256
host    all             grounded      127.0.0.1/32            scram-sha-256
```

```bash
sudo systemctl restart postgresql
```

---

## Application Setup

### 1. Create Application User

```bash
sudo useradd -r -s /bin/bash -d /opt/grounded -m grounded
sudo usermod -aG grounded grounded
```

### 2. Clone and Install Application

```bash
# Switch to app user
sudo -u grounded -i

# Clone repository (or copy files)
cd /opt/grounded
git clone https://github.com/your-org/grounded.git app
cd app

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create required directories
mkdir -p /opt/grounded/data/uploads
mkdir -p /var/log/grounded

# Set permissions
sudo chown -R grounded:grounded /opt/grounded
sudo chown -R grounded:grounded /var/log/grounded
```

### 3. Run Database Migrations

```bash
cd /opt/grounded/app
source venv/bin/activate

# Link environment file
ln -s /etc/grounded/.env .env

# Run migrations
alembic upgrade head
```

### 4. Test Startup

```bash
# Test configuration validation
python -c "from app.settings import settings; settings.validate_required_for_env()"

# Test database connection
python -c "from app.startup import run_startup_validation; run_startup_validation()"

# If successful, you should see:
# ✓ All startup validations passed
```

---

## Security Hardening

### 1. Firewall Configuration

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (for redirect to HTTPS)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# PostgreSQL should NOT be exposed
sudo ufw deny 5432/tcp
```

### 2. SSL/TLS with Let's Encrypt

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal
sudo systemctl enable certbot.timer
```

### 3. Nginx Reverse Proxy

Create `/etc/nginx/sites-available/grounded`:

```nginx
upstream grounded {
    server 127.0.0.1:8000;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    # SSL certificates (managed by Certbot)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/grounded.access.log;
    error_log /var/log/nginx/grounded.error.log;

    # Proxy settings
    location / {
        proxy_pass http://grounded;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Large file uploads
        client_max_body_size 50M;
    }

    # Health check (no auth required)
    location /health {
        proxy_pass http://grounded/health;
        access_log off;
    }

    location /ready {
        proxy_pass http://grounded/ready;
        access_log off;
    }
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/grounded /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Systemd Service

Create `/etc/systemd/system/grounded.service`:

```ini
[Unit]
Description=Grounded Application
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=notify
User=grounded
Group=grounded
WorkingDirectory=/opt/grounded/app
Environment="PATH=/opt/grounded/app/venv/bin"
EnvironmentFile=/etc/grounded/.env
ExecStart=/opt/grounded/app/venv/bin/uvicorn app.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 4 \
    --log-level info

# Restart policy
Restart=always
RestartSec=10
StartLimitBurst=5
StartLimitIntervalSec=60

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/grounded/data /var/log/grounded

# Resource limits
LimitNOFILE=65536
TimeoutStartSec=60
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

Enable and start service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable grounded
sudo systemctl start grounded

# Check status
sudo systemctl status grounded

# View logs
sudo journalctl -u grounded -f
```

---

## Monitoring

### 1. Health Checks

```bash
# Process alive
curl https://yourdomain.com/health

# Database + tables ready
curl https://yourdomain.com/ready
```

### 2. Application Logs

Logs are written in JSON format to `/var/log/grounded/app.log`:

```bash
# Tail logs
tail -f /var/log/grounded/app.log | jq .

# Search for errors
grep '"level":"ERROR"' /var/log/grounded/app.log | jq .

# Track specific request
grep '"request_id":"abc123"' /var/log/grounded/app.log | jq .
```

### 3. Rate Limit Monitoring

```bash
# Check rate limit violations
grep "Rate limit exceeded" /var/log/grounded/app.log | jq .
```

### 4. Log Rotation

Create `/etc/logrotate.d/grounded`:

```
/var/log/grounded/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 grounded grounded
    sharedscripts
    postrotate
        systemctl reload grounded >/dev/null 2>&1 || true
    endscript
}
```

---

## Startup Validation

The application **fails fast** with clear error messages if:

### Missing Environment Variables

```bash
# Example error:
Configuration validation failed:
  - DATABASE_URL is required
  - SECRET_KEY must be set with min 32 characters in production
  - OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai

Application will not start until this is resolved.
```

### Database Unreachable

```bash
# Check /ready endpoint
curl https://yourdomain.com/ready

# If database down:
{
  "status": "not_ready",
  "database": "disconnected",
  "error": "connection refused",
  "message": "Database connection failed"
}
```

### Missing Tables

```bash
# If migrations not run:
{
  "status": "not_ready",
  "database": "connected",
  "tables": "missing",
  "missing_tables": ["users", "toolkit_documents"],
  "message": "Run migrations: alembic upgrade head"
}
```

---

## Troubleshooting

### Application Won't Start

**Check systemd logs**:
```bash
sudo journalctl -u grounded -n 100 --no-pager
```

**Check startup validation**:
```bash
sudo -u grounded -i
cd /opt/grounded/app
source venv/bin/activate
python -c "from app.startup import run_startup_validation; run_startup_validation()"
```

### Database Connection Issues

**Test PostgreSQL**:
```bash
sudo -u grounded psql -h localhost -U grounded -d grounded -c "SELECT 1;"
```

**Check PostgreSQL logs**:
```bash
sudo tail -f /var/log/postgresql/postgresql-15-main.log
```

### Rate Limiting Issues

**Reset rate limits** (requires app restart):
```bash
sudo systemctl restart grounded
```

**Adjust limits** in `/etc/grounded/.env`:
```bash
RATE_LIMIT_AUTH_REQUESTS=10
RATE_LIMIT_RAG_REQUESTS=50
```

### SSL/TLS Issues

**Test certificate**:
```bash
sudo certbot certificates
curl -vI https://yourdomain.com
```

**Renew certificate manually**:
```bash
sudo certbot renew --dry-run
```

---

## Backup and Recovery

### Database Backup

```bash
# Backup database
sudo -u postgres pg_dump grounded > /backup/grounded-$(date +%Y%m%d).sql

# Restore database
sudo -u postgres psql grounded < /backup/grounded-20260123.sql
```

### Application Data

```bash
# Backup uploads
tar -czf /backup/uploads-$(date +%Y%m%d).tar.gz /opt/grounded/data/uploads/

# Restore uploads
tar -xzf /backup/uploads-20260123.tar.gz -C /
```

---

## Performance Tuning

### Uvicorn Workers

Adjust workers in systemd service based on CPU cores:

```bash
--workers 4  # Rule of thumb: (2 x cores) + 1
```

### PostgreSQL

Edit `/etc/postgresql/15/main/postgresql.conf`:

```ini
shared_buffers = 512MB              # 25% of RAM
effective_cache_size = 2GB           # 50-75% of RAM
work_mem = 16MB
maintenance_work_mem = 256MB
max_connections = 100
```

### Nginx

Edit `/etc/nginx/nginx.conf`:

```nginx
worker_processes auto;
worker_connections 1024;
keepalive_timeout 65;
client_max_body_size 50M;
```

---

## Security Checklist

- [ ] `ENV=prod` in environment file
- [ ] `SECRET_KEY` is 32+ characters and unique
- [ ] `COOKIE_SECURE=true` enforced
- [ ] PostgreSQL only listens on localhost
- [ ] Firewall configured (only 22, 80, 443 open)
- [ ] SSL/TLS certificate installed and auto-renewing
- [ ] Application runs as non-root user (`grounded`)
- [ ] File permissions: `/etc/grounded/.env` is 640
- [ ] Rate limiting enabled
- [ ] Structured logging enabled (JSON format)
- [ ] Health checks configured in load balancer
- [ ] Regular backups scheduled
- [ ] Log rotation configured

---

## Production Readiness Checklist

- [ ] All environment variables configured
- [ ] Database created with pgvector extension
- [ ] Migrations run successfully
- [ ] Startup validation passes
- [ ] `/health` returns 200
- [ ] `/ready` returns 200 with "tables": "present"
- [ ] Systemd service enabled and running
- [ ] Nginx reverse proxy configured with SSL
- [ ] Firewall rules applied
- [ ] Monitoring and alerting configured
- [ ] Backup strategy implemented
- [ ] Log rotation configured

---

For additional help, see [README.md](README.md) or contact your system administrator.
