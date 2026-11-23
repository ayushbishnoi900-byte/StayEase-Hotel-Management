# StayEase – College Presentation & Viva Guide

**Project Title:** StayEase – Hotel Management & Reservation System  
**Course:** B.Tech Computer Science & Engineering (Capstone Project)  
**Team Size:** 4 Students  
**Technology Stack:** Python FastAPI, PostgreSQL (Neon), SQLAlchemy, Argon2, JWT, HTML5/CSS3/JavaScript, Vercel

---

## Slide-by-Slide Presentation Structure

```
+-----------------------------------------------------------------------+
|                        STAYEASE PRESENTATION OUTLINE                  |
|                                                                       |
|  [Part A] Introduction & Motivation                                   |
|  [Part B] Problem Statement                                           |
|  [Part C] Proposed Solution                                           |
|  [Part D] Project Objectives                                          |
|  [Part E] Technology Stack Justification                              |
|  [Part F] System Architecture & Data Flow                             |
|  [Part G] Database Design & ER Diagram                                |
|  [Part H] Core Functional Modules & Live Demonstration                |
|  [Part I] Security Architecture & Vulnerability Mitigation             |
|  [Part J] Future Scope & Enhancements                                 |
|  [Part K] Conclusion                                                  |
|  [Part L] Individual Team Responsibilities & Viva Q&A Guide           |
+-----------------------------------------------------------------------+
```

---

## Part A: Project Introduction
StayEase is an enterprise-grade, cloud-ready Hotel Management & Reservation System engineered using modern web technologies. It bridges the gap between customer-facing hotel booking platforms (like Booking.com or Airbnb) and internal hotel property management systems (PMS) used by front desk and administrative staff.

The system empowers guests to view live room availability, reserve rooms, print official tax invoices, manage upcoming stays, and query a 24/7 digital assistant. Simultaneously, it equips hotel managers with an administrative dashboard to oversee bookings, occupancy rates, housekeeping cycles, staff records, and revenue metrics.

---

## Part B: Problem Statement
Independent boutique hotels and mid-sized hospitality businesses often face significant operational inefficiencies:
1. **Double-Booking Collisions**: Manual reservation books or poorly isolated databases lead to simultaneous bookings for the same room on overlapping dates.
2. **Security Vulnerabilities**: Many student and legacy hotel systems store plain-text passwords or vulnerable MD5/SHA1 hashes and lack Insecure Direct Object Reference (IDOR) guards.
3. **High Maintenance Overhead**: Heavy single-page frameworks (React/Angular) introduce complicated build pipelines, high bundle sizes, and dependency conflicts.
4. **Manual Billing & Invoicing**: Staff spend significant time calculating multi-night tariffs, taxes, and creating invoices manually.
5. **Customer Support Bottlenecks**: Front desk staff are overwhelmed with repetitive inquiries regarding check-in times, amenities, and pricing.

---

## Part C: Proposed Solution
StayEase resolves these operational pain points through:
1. **Mathematical Overlap Prevention Engine**: Server-side validation logic enforced with row-level database locks that guarantees zero overlapping reservations.
2. **Modern Security Hardening**: Industry-standard **Argon2id** password hashing, stateless signed **JWT tokens**, and strict ownership verification on all booking, payment, and invoice endpoints.
3. **High-Performance Architecture**: Asynchronous Python **FastAPI** backend with a lightweight, responsive vanilla frontend executing in $< 10\text{ms}$.
4. **Automated Billing & Digital Invoicing**: Instant multi-night calculation ($Nights \times Rate$) and printable PDF invoices generated at the click of a button.
5. **StayEase Assistant (In-House Conversational Concierge)**: A custom Python-driven intent extraction engine providing 24/7 answers from live database inventory without external API fees.

---

## Part D: Project Objectives
- **Zero Double-Bookings**: Ensure mathematical collision protection for overlapping date ranges across all room categories.
- **Role-Based Separation**: Strict boundary separation between Customer self-service actions and Administrator property management.
- **Transparent Academic Demonstration**: Safe, simulated checkout workflows ("Demo Online Payment" and "Cash at Hotel") with official disclaimers.
- **Serverless Cloud Deployment**: Seamless continuous deployment on Vercel backed by serverless Neon PostgreSQL.
- **Code Maintainability**: Clean, beginner-friendly Python code that any team member can confidently explain during university defense.

---

## Part E: Technology Stack Justification

```
+--------------------------------------------------------------------------+
| Layer           | Technology           | Why We Chose It                 |
+-----------------+----------------------+---------------------------------+
| Backend         | Python FastAPI       | Asynchronous ASGI, automatic    |
|                 |                      | Swagger interactive docs (/docs)|
+-----------------+----------------------+---------------------------------+
| Database        | PostgreSQL on Neon   | Serverless, auto-scaling, cloud |
|                 |                      | native with SSL encryption      |
+-----------------+----------------------+---------------------------------+
| ORM             | SQLAlchemy 2.0       | Type-safe queries, parameterized|
|                 |                      | queries prevent SQL injection   |
+-----------------+----------------------+---------------------------------+
| Passwords       | Argon2id (pwdlib)    | Winner of Password Hashing Comp,|
|                 |                      | memory-hard, GPU-resistant      |
+-----------------+----------------------+---------------------------------+
| Sessions        | JWT (python-jose)    | Stateless bearer authentication |
|                 |                      | with 24-hour expiration         |
+-----------------+----------------------+---------------------------------+
| Frontend        | HTML5 / CSS3 / JS    | Fast load times, zero framework |
|                 |                      | vulnerabilities, clean DOM      |
+-----------------+----------------------+---------------------------------+
| Deployment      | Vercel Serverless    | Global Edge CDN for assets,     |
|                 |                      | Lambda for Python serverless    |
+-----------------+----------------------+---------------------------------+
```

---

## Part F: System Architecture & Data Flow

```
                      +-----------------------------+
                      |       Client Browser        |
                      |  (Desktop / Tablet / Mobile)|
                      +--------------+--------------+
                                     |
               HTTPS Requests        |  Static Assets (HTML/CSS/JS)
               (JSON Payloads)       |  (Served via Vercel Edge CDN)
                                     v
                      +-----------------------------+
                      |      Vercel Serverless      |
                      |       Reverse Proxy         |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |     FastAPI Application     |
                      |          (main.py)          |
                      +--------------+--------------+
                                     |
          +--------------------------+--------------------------+
          |                          |                          |
          v                          v                          v
+-------------------+      +-------------------+      +-------------------+
|  Auth & Security  |      |  Booking Engine   |      | StayEase Assistant|
|  - JWT Bearer     |      |  - Date Overlaps  |      |  - Intent Engine  |
|  - Argon2 Hasher  |      |  - Row Locking    |      |  - Rate Limiter   |
|  - RBAC Guard     |      |  - Pricing Calc   |      |  - Dynamic DB Look|
+---------+---------+      +---------+---------+      +---------+---------+
          |                          |                          |
          +--------------------------+--------------------------+
                                     |
                                     v
                      +-----------------------------+
                      |       SQLAlchemy ORM        |
                      |     (Database Models)       |
                      +--------------+--------------+
                                     |
                       SSL Encrypted | Connection Pool
                                     v
                      +-----------------------------+
                      |    Neon Cloud PostgreSQL    |
                      |   (Serverless Database)     |
                      +-----------------------------+
```

---

## Part G: Database Design & Entity Relationship (ER)

```
+--------------------+        +---------------------+        +--------------------+
|     CUSTOMERS      |        |      BOOKINGS       |        |       ROOMS        |
+--------------------+        +---------------------+        +--------------------+
| id (PK)            | 1    * | id (PK)             | *    1 | id (PK)            |
| name               +------->| customer_id (FK)    |<-------+ room_number (UQ)   |
| email (UQ)         |        | room_id (FK)        |        | room_type          |
| password (Argon2)  |        | check_in            |        | price              |
| phone              |        | check_out           |        | capacity           |
| role (cust/admin)  |        | total_price         |        | status             |
| status (Active)    |        | guests              |        | description        |
| created_at         |        | status              |        | image_url          |
+--------------------+        | created_at          |        | housekeeping_status|
                              +----------+----------+        | last_cleaned       |
                                         | 1                 | created_at         |
                                         |                   +--------------------+
                                         | *
                              +----------v----------+
                              |      PAYMENTS       |
                              +---------------------+
                              | id (PK)             |
                              | booking_id (FK)     |
                              | amount              |
                              | payment_method      |
                              | payment_status      |
                              | transaction_ref     |
                              | payment_date        |
                              +---------------------+

+--------------------+        +---------------------+
|       STAFF        |        |   HOTEL_SETTINGS    |
+--------------------+        +---------------------+
| id (PK)            |        | id (PK)             |
| name               |        | hotel_name          |
| email (UQ)         |        | contact_email       |
| phone              |        | contact_phone       |
| designation        |        | hotel_address       |
| status (Active)    |        | check_in_time       |
| created_at         |        | check_out_time      |
+--------------------+        | cancellation_policy |
                              +---------------------+
```

### Relational Constraints
- **Referential Integrity**: `bookings.customer_id` and `bookings.room_id` enforce `ondelete="RESTRICT"` so customer history and booked rooms cannot be accidentally deleted.
- **Cascade Cleanup**: `payments.booking_id` enforces `ondelete="CASCADE"`.
- **Uniqueness**: `customers.email`, `rooms.room_number`, and `staff.email`.

---

## Part H: The Overlapping Reservation Algorithm

A critical interview/presentation question is: **"How does your backend prevent two guests from booking the same room on the same dates?"**

### Mathematical Condition:
Two time intervals $[CheckIn_A, CheckOut_A]$ and $[CheckIn_B, CheckOut_B]$ overlap **if and only if**:
$$CheckIn_A < CheckOut_B \quad \text{AND} \quad CheckOut_A > CheckIn_B$$

### Python / SQLAlchemy Query:
```python
overlapping = db.query(Booking).filter(
    Booking.room_id == requested_room_id,
    Booking.status == "Confirmed",
    Booking.check_in < requested_checkout,
    Booking.check_out > requested_checkin
).first()

if overlapping:
    raise HTTPException(
        status_code=409,
        detail="Room is already reserved for the selected dates."
    )
```

### Edge Cases Tested & Handled:
- **Exact Overlap**: Guest 2 picks identical dates $\rightarrow$ **Blocked (409)**
- **Inside Overlap**: Guest 2 picks dates inside an existing stay $\rightarrow$ **Blocked (409)**
- **Enclosing Overlap**: Guest 2 picks dates that start before and end after $\rightarrow$ **Blocked (409)**
- **Same-Day Turnover**: Guest 1 checks out at 11:00 AM on Day 5, and Guest 2 checks in at 2:00 PM on Day 5 $\rightarrow$ **Allowed** (since $CheckIn_B = CheckOut_A$, strict inequality prevents false positive).
- **Cancelled Stays**: Filter specifies `Booking.status == "Confirmed"`, so cancelled dates are instantly freed for new bookings.

---

## Part I: Security Implementation

1. **Password Security (Argon2id)**:
   - Uses `pwdlib` with Argon2id parameters.
   - Salted automatically with high memory cost ($64\text{MB}$), protecting against rainbow table and ASIC attacks.
2. **IDOR (Broken Object-Level Authorization) Protection**:
   - `customer_id` submitted by frontend forms is never trusted. The customer ID is read directly from the verified cryptographic payload of the JWT token.
   - For `/bookings/{id}`, `/bookings/{id}/invoice`, and `/bookings/cancel/{id}`, the system checks:
     ```python
     if booking.customer_id != current_user.id and current_user.role != "admin":
         raise HTTPException(status_code=403, detail="Forbidden")
     ```
3. **Role-Based Access Control (RBAC)**:
   - `require_admin` dependency gates all `/admin/*` endpoints. Non-admin users attempting access receive immediate `403 Forbidden` responses.
4. **SQL Injection Defense**:
   - 100% of database reads and writes use SQLAlchemy ORM expressions; zero raw string concatenation in SQL queries.
5. **Cross-Site Scripting (XSS) Sanitization**:
   - Dynamic user content in `app.js` is filtered through `escapeHTML()`, converting `<`, `>`, `&`, `"`, `'` to HTML character entities.
6. **Chatbot Rate Limiting**:
   - Sliding-window rate limiter (35 req/60s per client IP) mitigates server flooding.

---

## Part J: Future Scope
- **Payment Gateway Webhook**: Integration with live Stripe / Razorpay webhooks for production card authorization.
- **Automated Email/SMS Alerts**: Automated Twilio / SendGrid confirmation notifications upon booking and cancellation.
- **Dynamic Seasonal Pricing**: Rule-based price adjustments for holidays and peak occupancy weekends.
- **Multi-Property Support**: Expanding the data model to manage hotel chains across multiple geographical branches.

---

## Part K: Conclusion
The StayEase Hotel Management System proves that a college project can adhere to modern software engineering standards. By pairing Python FastAPI with Neon PostgreSQL and a clean Vanilla JS frontend, our team built an ultra-fast, visually premium, and secure application that completely eliminates double bookings, automates hotel operations, and passes 150 automated test scenarios.

---

## Part L: Individual Team Responsibilities & Presentation Guide

Each team member has a clearly defined module to explain during presentations:

### Student 1: Backend Lead & API Architect
- **Primary Modules**: `main.py`, `requirements.txt`, `vercel.json`
- **Topics to Present**:
  - Why FastAPI was chosen over Flask and Django (async speed, Pydantic validation, automatic `/docs` OpenAPI).
  - API architecture: 34 endpoints organized across Customer Auth, Rooms, Bookings, Payments, Staff, and Admin.
  - JWT token generation, expiration claims (`exp`), and Bearer authentication dependencies (`get_current_user`).
  - How Vercel serverless deployment works with `@vercel/python`.
- **Sample Viva Question**: *"How does FastAPI validate incoming data?"*  
  *Answer*: *"FastAPI uses Pydantic models. When a request hits an endpoint, Pydantic automatically validates types, string lengths, regex patterns, and date ranges. If any field is invalid, FastAPI returns an informative 422 Unprocessable Entity error before business logic runs."*

### Student 2: Database Engineer & Security Specialist
- **Primary Modules**: `database/models.py`, `database/database.py`, `database/init_db.py`
- **Topics to Present**:
  - Neon PostgreSQL serverless cloud database architecture and SQLAlchemy connection pooling (`pool_pre_ping=True`).
  - Entity-Relationship schema: Foreign keys, cascade vs restrict rules, unique constraints.
  - The mathematical overlapping date formula that prevents double bookings.
  - Argon2id password hashing and IDOR vulnerability mitigation.
- **Sample Viva Question**: *"Why did you use ondelete='RESTRICT' for rooms and customers?"*  
  *Answer*: *"To prevent orphaned records and accidental data loss. If a room has confirmed bookings, foreign key restriction prevents anyone from deleting that room, protecting financial and reservation integrity."*

### Student 3: Frontend Developer & UI/UX Specialist
- **Primary Modules**: `public/index.html`, `public/assets/style.css`, `public/assets/app.js`
- **Topics to Present**:
  - The StayEase visual brand: Luxury dark forest green (`#173f35`), soft gold accents (`#b77b38`), and linen cards.
  - Single Page Application (SPA) architecture: dynamic section toggling, modal dialog controllers, and asynchronous `fetch()` API integration.
  - Mobile responsiveness: CSS grid, flexbox, and media queries across desktop, tablet, and mobile breakpoints.
  - Official Invoice generator and print stylesheet (`@media print`).
- **Sample Viva Question**: *"Why did you choose Vanilla JavaScript over React?"*  
  *Answer*: *"Vanilla JS has zero bundle overhead, executes in under 10 milliseconds, eliminates npm security vulnerabilities, and allows all four team members to understand and explain every DOM interaction without framework abstraction."*

### Student 4: Chatbot Assistant, QA & Analytics Developer
- **Primary Modules**: `chatbot/assistant.py`, `tests/`, `test_backend.py`, `test_chatbot.py`, `TESTING_REPORT.md`
- **Topics to Present**:
  - StayEase Assistant: The 21-intent rule and extraction engine that provides 24/7 guest support and queries live database room tariffs without paid API tokens.
  - Sliding-window rate limiting algorithm to prevent server abuse.
  - The 150-test automated quality assurance suite running on an isolated in-memory test database.
  - Administrator Analytics: Real-time calculation of occupancy rates and Chart.js visualization.
- **Sample Viva Question**: *"Does your chatbot use ChatGPT or an LLM?"*  
  *Answer*: *"No, and we are completely transparent about that. For our college presentation, we designed a deterministic, intent-based Python engine connected directly to our hotel database. This guarantees 100% accurate factual answers about room pricing and policies with zero cost, zero API latency, and zero hallucinations."*
