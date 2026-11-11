# KYISA Competition Management System

**Kenya Youth Intercounty Sports Association**
Official platform for managing national youth intercounty sports competitions across all 47 Kenyan counties.

🌐 **Live:** [kyisa.org](https://kyisa.org)

---

## Overview

KYISA CMS is a full-stack competition management platform built for Kenya's official youth intercounty sports body. It handles the full lifecycle of national sports competitions — from county registration and player identity verification through to fixture scheduling, match reporting, referee management and results publication.

The system serves a multi-role internal portal for ~300 staff users across 47 counties, alongside a public-facing website for news, results and standings.

---

## Features

### County Registration & Payments
- County Sports Directors register their county and select sport disciplines
- M-Pesa STK push (Daraja API) for registration fee payment — funds sent directly to phone
- Bank slip upload as alternate payment path
- Treasurer reviews and approves county registrations

### Player Identity Verification (3-layer pipeline)
- **Prembly Kenya IPRS** — live lookup against Kenya's national ID database (dual concurrent endpoints merged for maximum data)
- **Prembly Face Comparison** — biometric check: uploaded passport photo vs government IPRS photo, 70% confidence threshold
- **Verifisha** — async IPRS verification via webhook callback
- **Huduma Kenya** — manual verification workflow
- Age eligibility auto-computed from date of birth
- Full audit trail per player per check

### Competition Management
- Group stage, knockout and hybrid competition formats
- Auto fixture generation (round-robin per pool)
- Pool standings with points, goal difference, goals scored
- Knockout bracket management
- Venue allocation

### Match Operations
- Squad submission with configurable pre-kickoff deadline
- Match reporting and event logging
- Statistics engine (top scorers, assists, disciplinary, fair play)
- Referee appointments and availability management
- Match report approval workflow

### Authentication & Access Control
- 18 user roles with dedicated dashboards and permissions
- JWT (8h access / 7d refresh with rotation and blacklisting) for API
- Session auth with 15-minute inactivity timeout for portal
- Magic OTP login links for new users (single-use, 72h expiry)
- Force-password-change middleware on first login
- Admin role-preview mode (test any role live without DB change)

### Communications
- Branded HTML email via Brevo API (bypasses SMTP port restrictions)
- Welcome emails with copy-to-clipboard password + one-click magic login
- Background-threaded email delivery with 3-attempt exponential backoff
- Full EmailLog audit trail
- Brevo inbound webhook for email centre inbox

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Django 6.0.2, Django REST Framework 3.16.1 |
| **Database** | PostgreSQL 16 (AWS RDS / Railway) |
| **Cache / Queue** | Redis, Celery |
| **Auth** | SimpleJWT, django-sessions |
| **Email** | django-anymail + Brevo |
| **Payments** | Safaricom Daraja API (M-Pesa STK Push) |
| **Identity** | Prembly Kenya (IPRS + Face Comparison), Verifisha |
| **Media Storage** | Cloudinary CDN |
| **Static Files** | WhiteNoise with Brotli/gzip compression |
| **API Docs** | drf-spectacular (OpenAPI 3 + Swagger UI) |
| **Frontend** | Django Templates, Bootstrap 5, Vanilla JS |
| **Server** | Gunicorn, Nginx |
| **Deployment** | AWS EC2, Docker, GitHub Actions CI/CD |

---

## User Roles

| Role | Responsibility |
|---|---|
| System Admin | Full platform oversight, user management |
| Secretary General | Executive oversight, appeals, exceptional approvals |
| Competition Manager | Create competitions, manage pools, generate fixtures |
| Soccer / Handball / Basketball / Volleyball Coordinator | Discipline-specific competition management (men & women) |
| Verification Officer | Player identity verification workflow |
| Treasurer | County payment review and approval |
| Referee | Match officiating, report submission |
| Team Manager | Squad submission, fixture viewing |
| County Sports Director | County registration, player and bench management |
| CEC Sports Member | View-only county and competition data |
| Scout | Browse verified players, build shortlists |
| Media Manager | Articles, photo albums, videos |
| Jury Chair | Appeals and disciplinary decisions |
| KICOSCA Officer | Parallel KICOSCA games management |

---

## API

REST API available at `/api/v1/` with JWT authentication.

Interactive docs: [`/api/docs/`](https://kyisa.org/api/docs/) *(staff login required)*

Endpoints cover: auth, competitions, fixtures, pools, venues, referees, teams, players, squads, match reports.

---

## Local Development

### Prerequisites
- Python 3.12+
- PostgreSQL
- Redis (optional — DummyCache used in dev)

### Setup

```bash
git clone https://github.com/Emannuh/KYISA.git
cd KYISA

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env — set SECRET_KEY, DATABASE_URL at minimum

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Environment Variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key (required) |
| `DATABASE_URL` | PostgreSQL connection string |
| `DEBUG` | `True` for local dev |
| `ALLOWED_HOSTS` | Comma-separated hostnames |
| `REDIS_URL` | Redis URL (optional in dev) |
| `STORAGE_BACKEND` | `cloudinary` / `s3` / `azure` / `gcs` / empty for local |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud name |
| `CLOUDINARY_API_KEY` | Cloudinary API key |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret |
| `PREMBLY_API_KEY` | Prembly Kenya live API key |
| `MPESA_CONSUMER_KEY` | Safaricom Daraja consumer key |
| `MPESA_CONSUMER_SECRET` | Safaricom Daraja consumer secret |
| `MPESA_SHORTCODE` | M-Pesa business shortcode |
| `MPESA_PASSKEY` | Lipa Na M-Pesa passkey |
| `MPESA_CALLBACK_URL` | Public URL for M-Pesa callbacks |
| `BREVO_API_KEY` | Brevo transactional email API key |
| `EMAIL_BACKEND` | `anymail.backends.brevo.EmailBackend` in production |

See `.env.example` for the full list.

---

## Deployment

The project deploys automatically via GitHub Actions on push to `main`.

**Production stack:**
- AWS EC2 (t2.micro) running Docker + Nginx
- AWS RDS PostgreSQL (db.t2.micro)
- Redis on EC2 (Docker)
- TLS via Let's Encrypt / Certbot (auto-renewing)
- Cloudinary for media file storage

**Manual migration (if needed):**
```bash
# SSH into EC2 or Railway console
.venv/bin/python manage.py migrate --noinput
```

---

## Project Structure

```
kyisa_cms/          # Django project — settings, urls, main views, email utils
accounts/           # Custom user model, 18 roles, JWT auth, permissions
competitions/       # Competitions, pools, fixtures, venues, standings
teams/              # County registration, player management, M-Pesa, Prembly
matches/            # Match reports, squad submissions, statistics engine
referees/           # Referee profiles, appointments, availability
appeals/            # Appeals and jury management
admin_dashboard/    # Activity logs, email centre, admin tools
news_media/         # Articles, photo albums, videos
kicosca/            # KICOSCA parallel games management
templates/          # All HTML templates (public website + 18-role portal)
static/             # CSS design system, JS, images
```

---

## Sports Covered

Football (Men & Women) · Volleyball (Men & Women) · Basketball 5x5 (Men & Women) · Basketball 3x3 (Men & Women) · Handball (Men & Women) · Beach Volleyball · Beach Handball

---

## License

Private — Kenya Youth Intercounty Sports Association. All rights reserved.

---

*Built and maintained by the KYISA IT Team · [it@kyisa.org](mailto:it@kyisa.org)*
