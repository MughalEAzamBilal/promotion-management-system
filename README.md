# Punjab School Education Department (SED)
## Teacher Service, Seniority & Promotion Management System
### Teacher Promotion Portal - Departmental Promotion Committee (DPC)

A modular web application developed in Python (Flask, SQLAlchemy, SQLite, Bootstrap 5, pandas, openpyxl, ReportLab) implementing the complete specifications of **PromotionManagementSystem Part 1 through Part 4**.
A production-ready enterprise web application developed in Python (Flask, SQLAlchemy, Bootstrap 5, pandas, openpyxl, ReportLab) implementing the complete statutory promotion framework for the School Education Department, Government of the Punjab.

---

## 3 User Roles & Control Hierarchy
## Quick Start (Local Development)

| Role | Primary Purpose | Capabilities |
| :--- | :--- | :--- |
| **SuperAdmin** | System Owner & Platform Controller | Complete master control over the entire system: manages Administrators (create/edit/deactivate), Google AdSense monetization & ad slots, system settings, statutory Promotion Rules (2014) & Sources, SQLite database snapshots/backups, and security audit logs. SuperAdmin can also perform all Admin and Teacher tasks. |
| **Admin** | Department / District Operator | Controls teachers and routine departmental tasks: manages teacher records (add, edit, soft delete), uploads Excel spreadsheets with preview and upsert support, verifies teacher profiles & qualifications, maintains official district seniority rolls (with civil service age tie-breakers), reviews teacher correction requests (Approve/Reject), runs promotion eligibility assessments, manages vacancy quotas (50% promotion / 50% direct), and generates PDF gazette printouts. |
| **Teacher** | Individual Educator Portal | Self-service access using CNIC / Personnel No: views verified personal dossier, updates contact info (mobile, email, address), submits educational & professional qualifications for departmental verification, views service timeline & district seniority ranking, submits structured Correction Requests with documentary evidence, and runs the interactive **Promotion Eligibility Simulator** with statutory rule citations. |

---

## Getting Started

### 1. Requirements
- Python 3.10+ (tested on Python 3.14)
- Dependencies installed: `Flask`, `SQLAlchemy`, `Werkzeug`, `pandas`, `openpyxl`, `reportlab`

### 1. Requirements & Dependencies
- Python 3.10+
- Install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Database Initialization & Seeding
To initialize the SQLite database (`instance/teacher_promotion.db`) with official Punjab Service Rules 2014, quotas, and test accounts:
To initialize the database schema and seed official Punjab Service Rules 2014, quotas, and initial accounts:
```bash
python init_db.py
```

### 3. Launch the Application
Start the server:
```bash
python seed_data.py
python run.py
```
Visit in your web browser: **`http://127.0.0.1:5000`**

### 3. Launching the Web Application
Start the Flask development server:
---

## Production Deployment to Real Hosting

For deploying to live web servers, cPanel, Linux VPS, or Cloud PaaS:

* **Production Guide**: See the complete step-by-step manual in [DEPLOYMENT_GUIDE.md](file:///c:/Users/Mughal%20e%20Azam%20Bilal/Downloads/WebProjects/PromotionManagementSystem/DEPLOYMENT_GUIDE.md).
* **WSGI Entry Point**: [`wsgi.py`](file:///c:/Users/Mughal%20e%20Azam%20Bilal/Downloads/WebProjects/PromotionManagementSystem/wsgi.py) (ready for Gunicorn, uWSGI, Passenger, Waitress).
* **PaaS Procfile**: [`Procfile`](file:///c:/Users/Mughal%20e%20Azam%20Bilal/Downloads/WebProjects/PromotionManagementSystem/Procfile) (ready for Render, Railway, Heroku).
* **Environment Configuration**: Copy [`.env.example`](file:///c:/Users/Mughal%20e%20Azam%20Bilal/Downloads/WebProjects/PromotionManagementSystem/.env.example) to `.env` and set `SECRET_KEY` and `DATABASE_URL`.

Quick production launch with Gunicorn:
```bash
python run.py
gunicorn wsgi:app --workers 4 --threads 2 --bind 0.0.0.0:5000
```

Visit in your web browser: **`http://127.0.0.1:5000`**
Quick production launch on Windows Server with Waitress:
```powershell
waitress-serve --listen=0.0.0.0:5000 wsgi:app
```

---

## Default Seeded User Accounts
## Default User Accounts

| Role | Username / CNIC | Password | Details |
| :--- | :--- | :--- | :--- |
| **SuperAdmin** | `superadmin` | `SuperAdmin@123` | System Owner (Complete control over system, ads, rules, admins, teachers) |
| **SuperAdmin** | `superadmin` | `SuperAdmin@123` | System Owner (Complete control over system, rules, admins, teachers) |
| **Admin** | `admin_lahore` | `Admin@123` | District Education Officer (SE) Lahore |
| **Admin** | `admin_rawalpindi` | `Admin@123` | District Education Officer (SE) Rawalpindi |
| **Teacher 1** | `35201-1234567-1` | `Teacher@123` | Muhammad Tariq (PST BS-14, Lahore) - Eligible for EST (Science) BS-15 |
| **Teacher 2** | `35201-2345678-2` | `Teacher@123` | Ayesha Bibi (EST BS-15, Lahore) - Eligible for SST (Science) BS-16 |
| **Teacher 3** | `35201-3456789-3` | `Teacher@123` | Zahid Mehmood (SST BS-16, Lahore) - Eligible for Headmaster BS-17 |
| **Teacher 4** | `35201-4567890-4` | `Teacher@123` | Farhan Ali (PST BS-14, Lahore) - Unverified profile & service shortfall |
| **Teacher** | `35201-1234567-1` | `Teacher@123` | Muhammad Tariq (PST BS-14, Lahore) |

*(Note: In production, change default passwords immediately after initial deployment.)*

---

## Core Features & Architecture

### 1. Statutory Promotion Rules Engine
- Built around official **Punjab School Education Department Service Rules 2014 (Notification No. SOR-III(S&GAD)1-19/2004(P))**.
- Evaluates:
  - Minimum regular service tenure in feeder scale (date-as-of calculation).
  - Prescribed academic degree level & subject match.
  - Mandatory professional teaching degree (B.Ed, M.Ed, ADE).
  - Departmental verification status.
  - Disciplinary clearance under PEEDA Act 2006.
  - Annual ACR / PER performance scores.
  - Seniority ranking within available 50% promotional vacancy quota.
- Strictly complies with regulatory disclaimer: Never declares *"Teacher has been promoted"*; outputs *"Eligible for consideration for promotion"*.

### 2. Bulk Excel Import, Preview & Upsert Engine
- Official styled template download (`.xlsx`) with guidance sheet.
- Pre-upload validation: detects invalid dates, incorrect CNIC lengths, internal duplicate rows, and database conflicts.
- Preview mode displays total rows, valid rows, new inserts, and updates before committing.
- Upsert mode safely updates existing records matching CNIC.

### 3. ReportLab PDF Generation
- Teacher Official Service & Promotion Dossier (3-page gazette style).
- District Seniority Roll with civil service ordering (regularization date + age tie-breaker).
- Promotion Eligibility Assessment Sheet with condition breakdown and signature blocks.

### 4. Google AdSense Subsystem
- SuperAdmin can configure Publisher ID, master ad toggle, Auto-ads script, and custom header injection.
- Test Mode generates safe placeholder banners to test placements without policy infractions.
- Customizable Ad Slots for Header, Content, and Footer with role-specific targeting.
1. **Statutory Promotion Rules Engine**: Strictly grounded in official Punjab SED Service Rules (Notification No. SOR-III(S&GAD)1-19/2004(P)) with quota zones and tie-breaking algorithms.
2. **Teacher Dossier & Self-Service Portal**: Mobile/email verification, qualifications audit, service chronology, structured correction request claims with tick-to-enable controls.
3. **Teacher Credentials & Password Helpdesk**: Self-service claim logging, administrative manual password dispatch via SMS/Email, and mass bulk password reset with safety safeguards.
4. **Excel Import / Export**: Pre-flight validation, preview table, atomic upsert, and automated credential provisioning.
5. **ReportLab PDF Gazette**: Official Departmental Promotion Committee (DPC) rolls, seniority lists, and retirement notifications with customizable official stamps and signatories.
6. **10-Minute Session Security**: Automatic inactivity timeout with watchdog alert and CSRF/session protection.
