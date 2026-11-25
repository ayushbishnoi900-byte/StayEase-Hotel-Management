# StayEase – Hotel Management SaaS Platform

> **A Multi-Tenant B2B Cloud ERP & Property Management System (PMS) for Hotel Owners and Staff**  
> Developed as a B.Tech Computer Science Final Year Major Project / Capstone by a team of four students.

[![Live Demo](https://img.shields.io/badge/Live%20Platform-Vercel%20Production-success?style=flat&logo=vercel&logoColor=white)](https://stay-ease-hotel-management.vercel.app)
[![API Documentation](https://img.shields.io/badge/API%20Docs-FastAPI%20Swagger-009688?style=flat&logo=fastapi&logoColor=white)](https://stay-ease-hotel-management.vercel.app/docs)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon%20Serverless-336791?style=flat&logo=postgresql&logoColor=white)](https://neon.tech/)
[![SQLAlchemy](https://img.shields.io/badge/ORM-SQLAlchemy%202.0-D71F00?style=flat)](https://www.sqlalchemy.org/)
[![Automated Tests](https://img.shields.io/badge/Automated%20Tests-154%20Passing-brightgreen?style=flat)](TESTING_REPORT.md)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 🌐 Live Deployment & Interactive Links

- **Live SaaS Platform**: [https://stay-ease-hotel-management.vercel.app](https://stay-ease-hotel-management.vercel.app)
- **Interactive Swagger API Docs**: [https://stay-ease-hotel-management.vercel.app/docs](https://stay-ease-hotel-management.vercel.app/docs)
- **Alternative ReDoc Docs**: [https://stay-ease-hotel-management.vercel.app/redoc](https://stay-ease-hotel-management.vercel.app/redoc)
- **GitHub Repository**: [https://github.com/ayushbishnoi900-byte/StayEase-Hotel-Management.git](https://github.com/ayushbishnoi900-byte/StayEase-Hotel-Management.git)

---

## 1. Project Overview & Business Model

**StayEase** is a modern, production-grade, multi-tenant **Hotel Management Software-as-a-Service (SaaS) Platform** designed exclusively for independent hoteliers, property managers, and their operational staff.

### Core Business Model Distinction
> ⚠️ **Important Architectural Model**:  
> StayEase is **NOT** a public B2C booking site where travelers register to book rooms.  
> StayEase is a **B2B Hospitality ERP & Operations Platform**.

1. **Hotel Owner Onboarding**: A hotel owner registers their business on StayEase, creates their property profile, and gains full administrative control over their hotel operations.
2. **Staff Account Delegation**: The owner provisions private accounts for employees across specialized departments (Managers, Receptionists, Housekeeping, Accountants, and Maintenance) with custom login credentials.
3. **No Public Guest Accounts**: Hotel guests do not register on StayEase. Instead, authorized front desk staff record guest profiles during walk-in, phone, or direct counter reservations.
4. **Multi-Tenancy by Design**: Each hotel’s data (rooms, reservations, guests, staff, payments, housekeeping tasks, and maintenance tickets) is strictly isolated using cryptographic tenant scoping (`hotel_id`).

---

## 2. Key System Architecture & Core Modules

### A. Hotel Owner Registration & Automated Tenant Provisioning
- **Self-Service Registration**: Owners register via `POST /auth/register-owner` with:
  - Personal Information: Full Name, Email, Phone, Password (Argon2id hashed).
  - Property Profile: Hotel Name, Category, Address, City, State, Country, Official Contact Phone, Official Email, and Initial Room Capacity.
- **Isolated Tenant Generation**: Automatically provisions a new `Hotel` record and links the owner user with role `owner` and `hotel_id`.
- **Property Settings Isolation**: Each owner can manage custom check-in/out times, contact details, and cancellation policies in **Hotel Settings** without cross-tenant interference.

### B. Staff Management & Role-Based Access Control (RBAC)
No public registration exists for employees. Staff accounts are created and managed strictly by property owners or general managers via the **Staff Management** module (`POST /admin/staff` and `PUT /admin/staff/{id}`):
- **Full Credential Control**: Owners set the staff member's Name, Email, Phone, Role, Designation, Department, and Initial Login Password.
- **Password Reset & Account Status**: Owners can reset staff passwords and toggle duty status (`Active`, `On Leave`, `Off Duty`, `Inactive`) at any time.

#### Supported Platform Roles:
| Role | Platform Access & View | Key Capabilities |
| :--- | :--- | :--- |
| **👑 Hotel Owner** (`owner`) | **Executive Owner Dashboard** | Complete control: Property configuration, staff onboarding, inventory, financial audit, and system oversight. |
| **👔 General Manager** (`manager`) | **Operations Portal** | Day-to-day operations, room catalog updates, reservation tracking, guest directory, and operational performance reports. |
| **🛎️ Receptionist** (`receptionist`) | **Front Desk & Reservations** | Walk-in reservations, phone bookings, guest check-in/check-out, live room availability matrix, and guest registration. |
| **🧹 Housekeeping** (`housekeeping`) | **Housekeeping Board** | Room cleanliness tracking (*Clean*, *Dirty*, *Cleaning in Progress*, *Inspection Needed*). Automatic flagging upon guest checkout. |
| **💳 Accountant** (`accountant`) | **Billing & Finance Portal** | Offline transaction processing (Cash, Card, UPI, Bank Transfer), official GST-compliant tax invoices, and revenue auditing. |
| **🔧 Maintenance** (`maintenance`) | **Facility & Work Orders** | Equipment issue ticketing, urgent room breakdowns (automatically sets room status to *Out of Order*), and repair tracking. |

### C. True Multi-Tenant Data Isolation
- **Row-Level Security**: Every query across `rooms`, `guests`, `reservations`, `payments`, `housekeeping`, `maintenance`, and `users` is scoped by `hotel_id`.
- **Zero Frontend Trust**: The server **never** trusts a `hotel_id` supplied in the request body. The tenant identity is extracted securely from the cryptographically signed JWT access token (`current_user.hotel_id`).
- **Cross-Tenant Guardrails**: Hotel A's staff or owner cannot view, query, update, or delete any record belonging to Hotel B.

### D. Front Desk Guest & Walk-In Reservation Engine
- **Direct Reservation Flow**: Front desk staff capture guest name, contact phone, optional email, address, and legal ID proof (Aadhaar, Passport, Driving License, Voter ID).
- **Double-Booking Collision Protection**: An ACID-compliant transaction algorithm prevents overlapping reservations for the same room number:
  $$\text{Overlap Condition: } (\text{CheckIn}_{\text{new}} < \text{CheckOut}_{\text{existing}}) \land (\text{CheckOut}_{\text{new}} > \text{CheckIn}_{\text{existing}})$$
- **Instant Tax Invoices**: Generates printable, branded invoices detailing daily room tariff, duration of stay, applicable GST/taxes, and payment receipt breakdown.

---

## 3. Pre-Configured Demo Accounts (For Viva & Presentation)

For college faculty evaluation, viva presentations, and quick testing, **Grand StayEase Palace** (Hotel ID 1) is pre-configured with 6 demo roles. You can log in using the credentials below or click the **One-Click Demo Login** chips in the web interface:

| Platform Role | Demo Email Address | Password | Demonstration Scope |
| :--- | :--- | :--- | :--- |
| **👑 Hotel Owner** | `admin@stayease.com` | `admin123` | Full Administrative Access, Hotel Settings, Staff Onboarding |
| **👔 General Manager** | `manager@stayease.com` | `staff123` | Operations Oversight, Room Inventory, Reservation Management |
| **🛎️ Receptionist** | `receptionist@stayease.com` | `staff123` | Front Desk, Guest Check-In/Out, Walk-in Reservations |
| **🧹 Housekeeping** | `housekeeping@stayease.com` | `staff123` | Room Cleaning Status, Turn-Down Readiness |
| **💳 Accountant** | `accountant@stayease.com` | `staff123` | Invoicing, Payment Tracking, Revenue Audits |
| **🔧 Maintenance** | `maintenance@stayease.com` | `staff123` | Work Orders, Facility Repairs, Defect Reporting |

---

## 4. Technology Stack & Technical Rationale

| Component | Technology | Technical Advantage & Rationale |
| :--- | :--- | :--- |
| **Backend Framework** | **Python FastAPI 0.115+** | Asynchronous ASGI execution, automatic request validation via Pydantic v2, and auto-generated OpenAPI 3.1 Swagger documentation. |
| **Database** | **PostgreSQL 16 (Neon Serverless)** | Relational ACID compliance, connection pooling (`pool_size=10`, `max_overflow=20`), SSL encryption, and cloud auto-scaling. |
| **ORM & Schema** | **SQLAlchemy 2.0** | Object-Relational Mapping with parameterized SQL queries preventing SQL injection vulnerabilities. |
| **Password Security** | **Argon2id (`pwdlib`)** | Memory-hard password hashing algorithm resistant to GPU cracking and side-channel timing attacks. |
| **Authentication** | **JWT (`python-jose`)** | Stateless, signed HMAC-SHA256 Bearer tokens containing claims (`sub`, `role`, `hotel_id`, `exp`). |
| **Frontend** | **Vanilla HTML5, CSS3, ES6+ JavaScript** | Ultra-responsive performance ($< 15\text{ms}$ script parse), zero third-party framework bundle overhead, and cross-browser consistency. |
| **Deployment** | **Vercel Serverless (WSGI/ASGI Bridge)** | Edge CDN distribution for static assets and autoscaling serverless execution for backend endpoints. |
| **Test Automation** | **Python `unittest` & TestClient** | 154 automated test cases covering authentication, multi-tenancy, collision prevention, and RBAC security. |

---

## 5. Project Directory Structure

```text
StayEase/
├── chatbot/                     # AI Concierge & Chatbot Engine
│   ├── __init__.py
│   └── assistant.py             # Rule/intent parser, DB availability engine, rate limiter
├── database/                    # Database Architecture & Connection Layer
│   ├── __init__.py
│   ├── database.py              # SQLAlchemy engine, connection pooling, get_db dependency
│   ├── init_db.py               # Auto-initialization, self-healing schema, and seed script
│   └── models.py                # Database models (Hotel, User, Room, Guest, Reservation, Payment, etc.)
├── public/                      # Single Page Application Frontend
│   ├── assets/
│   │   ├── app.js               # Frontend business logic, state store, authFetch, modal handlers
│   │   └── style.css            # Responsive luxury theme, role badges, modal styling, print invoices
│   └── index.html               # Semantic HTML5 layout, owner dashboard, role views, modals
├── tests/                       # Modular Unit Test Suites (52 tests)
│   ├── __init__.py
│   ├── base.py                  # In-memory SQLite test fixture & authenticated client helpers
│   ├── test_admin.py            # Dashboard metrics, staff CRUD, housekeeping, settings tests
│   ├── test_auth.py             # Owner registration, login, JWT issuance, profile updates
│   ├── test_bookings.py         # Reservation engine, past-date validation, double-booking prevention
│   ├── test_chatbot.py          # Chatbot intent matching, rate limiting, room query tests
│   ├── test_payments.py         # Billing transactions, invoice generation, payment status updates
│   ├── test_rooms.py            # Room catalog, category/price filters, deletion constraints
│   └── test_security.py         # IDOR barriers, RBAC authorization, SQL injection safety
├── .env.example                 # Environment variable template with safe placeholders
├── .gitignore                   # Git exclusions (bytecode, virtual environments, .env secrets)
├── main.py                      # FastAPI application entrypoint, lifecycle, and core endpoints
├── saas_routes.py               # Dedicated multi-tenant SaaS REST API router
├── PRESENTATION_GUIDE.md        # Comprehensive Viva & Capstone presentation guide
├── README.md                    # Project documentation (this file)
├── requirements.txt             # Locked Python production dependencies
├── test_backend.py              # End-to-end backend integration test runner (76 tests)
├── test_chatbot.py              # Standalone chatbot test runner (26 tests)
├── TESTING_REPORT.md            # Detailed QA audit report with test results & metrics
└── vercel.json                  # Vercel serverless build and routing configuration
```

---

## 6. REST API Endpoints Overview

The platform exposes a comprehensive RESTful API documented interactively via Swagger UI at `/docs`:

### Authentication & Tenant Provisioning
- `POST /auth/register-owner` – Onboards a new hotel owner, creates property profile, and initializes tenant.
- `POST /login` – Authenticates owner or staff credentials, returns signed JWT access token with role and `hotel_id`.
- `GET /me` – Returns current authenticated profile and hotel tenant details.

### Hotel Profile & Settings
- `GET /admin/settings` or `GET /api/hotel/settings` – Retrieves current hotel configuration (scoped to tenant).
- `PUT /admin/settings` or `PUT /api/hotel/settings` – Updates hotel name, contact details, timings, and policies.
- `GET /admin/dashboard` or `GET /api/hotel/overview` – Returns live operational statistics (Rooms, Occupancy, Revenue, Staff).

### Staff Management (RBAC)
- `GET /admin/staff` or `GET /api/staff` – Lists staff members belonging exclusively to the authenticated hotel.
- `POST /admin/staff` or `POST /api/staff` – Creates employee account with custom role and password.
- `GET /admin/staff/{id}` – Retrieves individual staff member details.
- `PUT /admin/staff/{id}` or `PUT /api/staff/{id}` – Updates staff designation, department, status, or resets password.
- `DELETE /admin/staff/{id}` or `DELETE /api/staff/{id}` – Removes staff member from the hotel directory.

### Room Inventory
- `GET /rooms` or `GET /api/rooms` – Lists rooms (scoped by tenant, filterable by type, price, and availability).
- `POST /rooms` or `POST /api/rooms` – Adds a new room to inventory (with duplicate room number validation).
- `GET /rooms/{id}` – Retrieves room specifications and amenities.
- `PUT /rooms/{id}` or `PUT /api/rooms/{id}` – Updates tariff, capacity, description, or operational status.
- `DELETE /rooms/{id}` or `DELETE /api/rooms/{id}` – Deletes room (blocked if active reservations exist).

### Front Desk Reservations & Guests
- `GET /bookings` or `GET /api/reservations` – Lists tenant reservations with date filters.
- `POST /bookings` or `POST /api/reservations` – Creates confirmed reservation with collision prevention.
- `GET /bookings/{id}` – Retrieves full reservation breakdown and stay dates.
- `PUT /bookings/cancel/{id}` – Cancels reservation and releases room back to available inventory.
- `GET /bookings/{id}/invoice` – Generates printable GST-compliant invoice breakdown.
- `GET /admin/customers` or `GET /api/guests` – Displays private hotel guest directory.

### Housekeeping & Maintenance
- `GET /admin/housekeeping` or `GET /api/housekeeping` – Retrieves room cleanliness status board.
- `PUT /admin/housekeeping/{id}` or `PUT /api/housekeeping/{id}` – Updates cleaning status (*Clean*, *Dirty*, *In Progress*).
- `GET /api/maintenance` – Retrieves maintenance tickets and equipment repair logs.
- `POST /api/maintenance` – Logs new repair ticket with urgency level.
- `PUT /api/maintenance/{id}` – Updates repair status or marks task completed.

### Billing & Analytics
- `GET /admin/payments` or `GET /api/payments` – Lists payment transactions across cash, card, UPI, and bank transfer.
- `PUT /admin/payments/{id}/status` – Updates transaction settlement status (*Completed*, *Refunded*, *Failed*).
- `GET /admin/analytics` or `GET /api/reports/analytics` – Aggregates occupancy rates, revenue trends, and category performance.

---

## 7. Local Installation & Setup Guide

### Prerequisites
- Python 3.10 or higher
- Git
- Web browser (Chrome, Safari, Firefox, Edge)

### Step 1: Clone the Repository
```bash
git clone https://github.com/ayushbishnoi900-byte/StayEase-Hotel-Management.git
cd StayEase-Hotel-Management
```

### Step 2: Create and Activate Virtual Environment
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

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy the sample environment file:
```bash
cp .env.example .env
```
Edit `.env` to configure your settings:
```env
# Neon Cloud PostgreSQL Connection URL (SSL Required)
DATABASE_URL=postgresql://username:password@hostname.neon.tech/stayease?sslmode=require

# 32-byte Cryptographic Secret Key for JWT
SECRET_KEY=generate-a-secure-32-byte-hex-key-here

# Default Hotel 1 Demo Administrator Account
ADMIN_NAME=StayEase Administrator
ADMIN_EMAIL=admin@stayease.com
ADMIN_PASSWORD=admin123
```
*(If `DATABASE_URL` is omitted, the application automatically falls back to an offline local SQLite database `stayease_local.db`).*

### Step 5: Initialize Database & Seed Starter Data
```bash
python3 database/init_db.py
```

### Step 6: Start the Development Server
```bash
uvicorn main:app --reload --port 8000
```
Open your browser:
- **Application Portal**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Swagger API Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 8. Automated Test Suite Execution

The project includes **154 automated test cases** that execute against isolated in-memory SQLite fixtures without affecting cloud database records:

```bash
# 1. Run Modular Unit Tests (52 tests across 8 modules):
python3 -m unittest discover tests

# 2. Run Integrated Backend API Test Suite (76 tests):
DATABASE_URL="sqlite:///:memory:" python3 test_backend.py

# 3. Run Chatbot Intent & NLP Test Suite (26 tests):
DATABASE_URL="sqlite:///:memory:" python3 test_chatbot.py
```

### Test Verification Summary:
- **Modular Unittests**: `52 passed, 0 failed`
- **Backend API Suite**: `76 passed, 0 failed`
- **Chatbot Suite**: `26 passed, 0 failed`
- **Total**: **154 Passed / 100% Pass Rate**

For a detailed breakdown of test cases, edge scenarios, and IDOR validation, refer to [TESTING_REPORT.md](TESTING_REPORT.md).

---

## 9. Vercel Cloud Deployment

The repository includes pre-configured `vercel.json` routing for seamless continuous deployment:

### Deploying via GitHub Integration
1. Push your changes to GitHub:
   ```bash
   git add .
   git commit -m "feat: complete multi-tenant hotel SaaS platform"
   git push origin main
   ```
2. In the [Vercel Dashboard](https://vercel.com/):
   - Click **"Add New Project"** and select your `StayEase-Hotel-Management` repository.
   - Under **Environment Variables**, configure:
     - `DATABASE_URL`: Your Neon PostgreSQL connection string.
     - `SECRET_KEY`: A secure 64-character hex key.
   - Click **Deploy**. Vercel will build the serverless functions and host the static assets across its global CDN.

---

## 10. Capstone Team Responsibilities (Team of 4 Students)

| Student Member | Project Role | Core Engineering Responsibilities |
| :--- | :--- | :--- |
| **Student 1** | **System Architect & Backend Lead** | Multi-tenant SaaS routing (`saas_routes.py`), FastAPI core (`main.py`), JWT authentication, Argon2id security, and Vercel serverless architecture. |
| **Student 2** | **Database & Security Specialist** | Entity-Relationship schema (`database/models.py`), PostgreSQL indexing, connection pooling, ACID double-booking collision prevention, and IDOR protection. |
| **Student 3** | **Frontend & UI/UX Developer** | Responsive Single Page Application (`public/index.html`), custom luxury theme (`style.css`), role-specific dashboard views, and printable GST tax invoice styling. |
| **Student 4** | **QA, Analytics & Chatbot Engineer** | Automated test development (`tests/`, 154 test scenarios), 24/7 AI concierge (`assistant.py`), rate limiting, and Chart.js financial analytics. |

For detailed viva preparation questions, architecture diagrams, and examiner presentation scripts, refer to [PRESENTATION_GUIDE.md](PRESENTATION_GUIDE.md).

---

## 11. Security Best Practices & Hygiene

- **Strict Environment Isolation**: Credentials, database URLs, and secret keys are managed through `.env` files strictly excluded by `.gitignore`.
- **Argon2id Password Storage**: Passwords are never stored in plain text. Argon2id incorporates memory cost ($m = 65536$), time cost ($t = 3$), and parallelism ($p = 4$) to withstand brute-force attacks.
- **SQL Injection Prevention**: All database interactions use SQLAlchemy ORM parameterized statements, preventing raw string concatenation.
- **Cross-Site Scripting (XSS) Sanitization**: Dynamic UI elements render through safe DOM operations (`textContent` and sanitized template nodes).

---

## 12. License & Academic Attribution

This project is open-source software licensed under the **[MIT License](LICENSE)**. Created for academic demonstration and university capstone evaluation.
