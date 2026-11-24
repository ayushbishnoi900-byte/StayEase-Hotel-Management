# StayEase – Hotel Management SaaS Platform

> **A Multi-Tenant B2B Cloud ERP & Operations System for Hotel Owners and Staff**  
> Developed as a B.Tech Computer Science College Capstone Project by a team of four students.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon%20Serverless-336791?style=flat&logo=postgresql&logoColor=white)](https://neon.tech/)
[![SQLAlchemy](https://img.shields.io/badge/ORM-SQLAlchemy%202.0-D71F00?style=flat)](https://www.sqlalchemy.org/)
[![Vercel](https://img.shields.io/badge/Deploy-Vercel-000000?style=flat&logo=vercel&logoColor=white)](https://vercel.com/)
[![Tests](https://img.shields.io/badge/Automated%20Tests-154%20Passed-brightgreen?style=flat)](TESTING_REPORT.md)

---

## 1. Project Introduction

**StayEase** is a production-grade, multi-tenant **Hotel Management SaaS Platform** designed exclusively for hotel owners and their authorized operational staff. 

**Important Business Model**:
StayEase is **NOT** a public B2C hotel room booking directory. It is an enterprise **Hospitality ERP & Property Management System (PMS)**. A hotel owner registers their property on StayEase, configures room catalogs, delegates staff accounts across specialized departments, and manages their entire property digitally.

Guests are operational customer records logged by front-desk staff (supporting walk-ins, phone inquiries, and corporate reservations) — eliminating paper registers and manual spreadsheet tracking.

---

## 2. Key Architecture & Features

### A. Dedicated Hotel Owner Registration & Tenant Provisioning
- **Onboarding Flow (`POST /auth/register-owner`)**: Hotel owners register with their personal credentials and property profile (Hotel Name, Category, Address, Total Rooms, Contact Details).
- **Auto-Provisioning**: Upon registration, an isolated `Hotel` tenant and `owner` user account are provisioned, seeded with starter room inventory, and immediately granted executive dashboard access.

### B. Multi-Role Staff Account Delegation & RBAC
Hotel owners and general managers can create employee accounts with strictly enforced Role-Based Access Control (RBAC):
1. **Hotel Owner (`owner`)**: Full executive control over property profile, staff delegation, rooms, billing, and system configuration.
2. **General Manager (`manager`)**: Day-to-day operations, staff directory oversight, inventory management, and performance reports.
3. **Front Desk Receptionist (`receptionist`)**: Walk-in & phone reservation logging, guest check-in/out, live room availability, and guest directory.
4. **Housekeeping Lead (`housekeeping`)**: Real-time room cleanliness tracking (*Clean*, *Dirty*, *In Progress*, *Inspection Needed*). Automatically marks rooms *Dirty* upon guest check-out.
5. **Hotel Accountant (`accountant`)**: Offline payment settlements (Cash, Card, UPI, Bank Transfer), official GST tax invoice generation, and financial auditing.
6. **Facility Maintenance (`maintenance`)**: Physical/electrical repair ticketing with priority levels (*Low*, *Medium*, *High*, *Urgent*). Urgent priority marks rooms Out-of-Order.

### C. Multi-Tenant Data Isolation
- Strict row-level tenant scoping using foreign key `hotel_id` across all relational entities: `rooms`, `guests`, `reservations`, `payments`, `housekeeping`, `maintenance`, and `users`.
- Backend endpoints automatically source `current_user.hotel_id` from cryptographically verified JWT session tokens.
- Cross-tenant data leakage is strictly blocked with comprehensive automated multi-tenancy tests.

### D. Front Desk Operations & Walk-In Desk
- Fast reservation workflow for counter walk-ins and phone calls.
- Collects government identification proof (Aadhaar, Passport, Driver's License, Voter ID) and contact details into the hotel's private **Guest Directory**.
- Collision prevention prevents double-booking rooms across overlapping stay dates.

### E. Live Demo Evaluator Accounts
Pre-seeded demo credentials for instant evaluation across every tier:

| Role | Email Address | Password | Designated Permissions |
| :--- | :--- | :--- | :--- |
| **👑 Hotel Owner** | `admin@stayease.com` | `admin123` | Full Property Access (Dashboard, Staff, Settings, CRUD) |
| **👔 General Manager** | `manager@stayease.com` | `staff123` | Operations, Staff Oversight, Room Management, Reports |
| **🛎️ Receptionist** | `receptionist@stayease.com` | `staff123` | Front Desk, Walk-Ins, Guest Check-In/Out, Payments |
| **🧹 Housekeeping** | `housekeeping@stayease.com` | `staff123` | Room Cleanliness Board, Quick Status Updates |
| **💳 Accountant** | `accountant@stayease.com` | `staff123` | Billing Transactions, Financial Reports, Invoicing |
| **🔧 Maintenance** | `maintenance@stayease.com` | `staff123` | Equipment Defect Tickets, Room Repair Resolution |

---

## 3. Technology Stack

| Layer | Technology | Justification |
| :--- | :--- | :--- |
| **Backend Framework** | Python FastAPI | High-performance, asynchronous REST API with automatic OpenAPI interactive documentation (`/docs`). |
| **Database** | PostgreSQL on Neon | Serverless, autoscaling cloud database with SSL encryption. |
| **ORM & Migrations** | SQLAlchemy 2.0 | Type-safe queries, parameterized statements (preventing SQL injection), and relationship modeling. |
| **Password Security** | Argon2id (`pwdlib`) | State-of-the-art password hashing resistant to GPU and side-channel attacks. |
| **Authentication** | JWT (`python-jose`) | Stateless, signed Bearer tokens with configurable expiration. |
| **Frontend** | HTML5, CSS3, Vanilla JS | Ultra-fast load times ($< 10\text{ms}$ execution), zero dependency vulnerabilities, and easy to explain. |
| **Deployment** | Vercel Serverless | Global CDN serving static assets and Python Serverless functions powering API routes. |
| **Testing** | Python `unittest` | Comprehensive 150-test automated suite running against isolated in-memory databases. |

---

## 4. Project Folder Structure

```text
StayEase/
├── chatbot/                     # Python Chatbot Assistant module
│   ├── __init__.py
│   └── assistant.py             # 21 intent patterns, DB query engine, sliding-window rate limiter
├── database/                    # Database models and session management
│   ├── __init__.py
│   ├── database.py              # SQLAlchemy engine, connection pooling, and get_db dependency
│   ├── init_db.py               # Safe database initialization and sample room seeder
│   └── models.py                # Database models: Room, Customer, Booking, Payment, Staff, HotelSetting
├── public/                      # Static frontend assets served by Vercel / FastAPI
│   ├── assets/
│   │   ├── app.js               # Frontend business logic, API fetch calls, and modal controllers
│   │   └── style.css            # Luxury dark green & gold hospitality theme, responsive layout
│   └── index.html               # Single-page application markup with modals & dashboard
├── tests/                       # Modular automated test suites (48 tests)
│   ├── __init__.py
│   ├── base.py                  # In-memory SQLite fixture and test helpers
│   ├── test_admin.py            # Dashboard metrics, staff, housekeeping, settings tests
│   ├── test_auth.py             # Registration, login, JWT, profile tests
│   ├── test_bookings.py         # Booking engine, past dates, overlap collisions, cancellations
│   ├── test_chatbot.py          # Assistant conversational intent scenarios
│   ├── test_payments.py         # Transaction records, owner isolation, refunds
│   ├── test_rooms.py            # Room CRUD, category/price filters, deletion guards
│   └── test_security.py         # IDOR barriers, RBAC checks, SQL injection safety
├── .env.example                 # Environment configuration template (safe placeholder)
├── .gitignore                   # Git exclusion rules (protects credentials, bytecode, db files)
├── main.py                      # FastAPI application entrypoint with 34 endpoints
├── PRESENTATION_GUIDE.md        # Comprehensive college presentation & viva guide
├── README.md                    # Project documentation (this file)
├── requirements.txt             # Python dependencies
├── test_backend.py              # Integrated end-to-end backend test runner (76 tests)
├── test_chatbot.py              # Standalone chatbot test runner (26 tests)
├── TESTING_REPORT.md            # Detailed quality assurance & audit report
└── vercel.json                  # Vercel deployment configuration
```

---

## 5. Local Installation & Setup

### Prerequisites
- Python 3.10, 3.11, 3.12, 3.13, or 3.14
- Git
- Web browser (Chrome, Firefox, Safari, Edge)

### Step 1: Clone the Repository
```bash
git clone https://github.com/your-username/StayEase.git
cd StayEase
```

### Step 2: Create and Activate a Virtual Environment
```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows (Command Prompt)
python -m venv venv
venv\Scripts\activate

# Windows (PowerShell)
python -m venv venv
venv\Scripts\Activate.ps1
```

### Step 3: Install Required Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Create a local `.env` file from the provided `.env.example`:
```bash
cp .env.example .env
```
Open `.env` in any text editor and fill in your configuration:
```env
# Neon PostgreSQL Connection URL
DATABASE_URL=postgresql://username:password@hostname.neon.tech/stayease?sslmode=require

# 32-byte JWT Secret Key
SECRET_KEY=your-secret-key-here-change-this

# Initial Admin Credentials
ADMIN_NAME=StayEase Administrator
ADMIN_EMAIL=admin@stayease.com
ADMIN_PASSWORD=admin123
```

> **Offline / Local Fallback**: If `DATABASE_URL` is omitted, the application will automatically initialize a local SQLite database (`stayease_local.db`) for testing and demonstration.

### Step 5: Initialize & Seed the Database
Run the safe seeder script to create database tables and seed sample rooms and the admin account:
```bash
python3 database/init_db.py
```

### Step 6: Start the Local Development Server
```bash
uvicorn main:app --reload --port 8000
```
Open your web browser and navigate to:
- **Application Frontend**: `http://127.0.0.1:8000/`
- **Interactive Swagger API Docs**: `http://127.0.0.1:8000/docs`
- **ReDoc API Reference**: `http://127.0.0.1:8000/redoc`

---

## 6. Default Demo Credentials

| Role | Email Address | Password | Permissions |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@stayease.com` | `admin123` | Full Access (Dashboard, Staff, Housekeeping, Analytics, Room CRUD) |
| **Sample Guest** | *(Register via UI)* | *(Min 8 chars)* | Customer Access (Browse Rooms, Book, View Bookings, Cancel, Invoices) |

---

## 7. Running the Automated Test Suites

The project features a **150-test automated verification suite** that runs in an isolated in-memory database without altering your cloud database.

```bash
# 1. Run all modular tests (48 tests):
python3 -m unittest discover tests

# 2. Run the integrated backend test runner (76 tests):
python3 test_backend.py

# 3. Run the chatbot conversation test runner (26 tests):
python3 test_chatbot.py
```
For detailed test coverage, see [TESTING_REPORT.md](TESTING_REPORT.md).

---

## 8. Deployment Guide (Vercel)

StayEase is pre-configured for one-click deployment to **Vercel Serverless**.

### Option A: Deploy via GitHub (Recommended)
1. Push your code to GitHub:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: StayEase Hotel Management System"
   git branch -M main
   git remote add origin https://github.com/your-username/StayEase.git
   git push -u origin main
   ```
2. Log in to [Vercel](https://vercel.com/) and click **"Add New" $\rightarrow$ "Project"**.
3. Select your `StayEase` GitHub repository and click **Import**.
4. In the **Environment Variables** section, add:
   - `DATABASE_URL`: Your Neon PostgreSQL pooled connection string.
   - `SECRET_KEY`: A secure 64-character random string.
5. Click **Deploy**. Vercel will build the Python serverless function and static assets.

### Option B: Deploy via Vercel CLI
```bash
npm install -g vercel
vercel login
vercel
# When prompted, add DATABASE_URL and SECRET_KEY as environment variables
vercel --prod
```

---

## 9. Team Responsibilities (Team of 4 Students)

| Member | Role | Primary Modules & Presentation Topics |
| :--- | :--- | :--- |
| **Student 1** | **Backend Lead & System Architect** | `main.py`, FastAPI routers, JWT token creation, Argon2 hashing, request/response Pydantic schemas, and Vercel serverless deployment. |
| **Student 2** | **Database & Security Specialist** | `database/models.py`, `database/database.py`, Neon PostgreSQL connection pooling, foreign keys, IDOR prevention, and double-booking collision algorithm. |
| **Student 3** | **Frontend & UI/UX Developer** | `public/index.html`, `public/assets/style.css`, luxury hospitality visual theme, mobile responsive media queries, modal workflows, and printable invoice styling. |
| **Student 4** | **Chatbot, QA & Analytics Developer** | `chatbot/assistant.py`, 24/7 conversational concierge, rate limiting, `tests/` automated test suite, Admin analytics dashboard, and Chart.js integration. |

---

## 10. Security & Credential Hygiene

- **`.env` Protection**: The `.gitignore` file strictly excludes `.env` to prevent private keys and database passwords from being exposed on GitHub.
- **Rotating Neon Credentials**: If your database credentials were ever shared publicly:
  1. Open the [Neon Console](https://console.neon.tech/).
  2. Select your StayEase project $\rightarrow$ **Settings** $\rightarrow$ **Reset Password**.
  3. Update `DATABASE_URL` in your local `.env` and in your Vercel Project Settings.
- **Rotating Secret Key**:
  1. Generate a new secret key: `python3 -c "import secrets; print(secrets.token_hex(32))"`
  2. Update `SECRET_KEY` in `.env` and Vercel. Existing tokens will gracefully expire.

---

## 11. License & Academic Attribution

This project is developed for academic purposes under the **MIT License**. Free to use, adapt, and learn from for university coursework and capstone evaluations.
