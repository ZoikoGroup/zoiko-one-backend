
# Zoiko One Backend 🚀

A FastAPI backend for the Zoiko One business application platform.

---

## ⚙️ Phase 1 — First Time Setup

### Step 1: Install Python
Download Python 3.11 or newer from https://python.org  
During install on Windows, **check "Add Python to PATH"**

Verify: open terminal and run:
```bash
python --version
# Should print: Python 3.11.x
```

### Step 2: Clone / open this project
```bash
cd zoiko-one-backend
```

### Step 3: Create a virtual environment
```bash
# Create it
python -m venv venv

# Activate it — Windows:
venv\Scripts\activate

# Activate it — Mac/Linux:
source venv/bin/activate

# You should see (venv) at the start of your terminal prompt
```

### Step 4: Install all packages
```bash
pip install -r requirements.txt
```

---

## ⚙️ Phase 2 — Database Setup

### Step 5: Install PostgreSQL
Download from https://postgresql.org/download  
Remember the password you set for the `postgres` user.

### Step 6: Create the database
Open pgAdmin (comes with PostgreSQL) or psql and run:
```sql
CREATE DATABASE zoiko_db;
```

### Step 7: Configure your .env file
Open `.env` and update the DATABASE_URL with your actual password:
```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD_HERE@localhost:5432/zoiko_db
```

---

## ▶️ Running the Server

```bash
# Make sure venv is activated first!
uvicorn app.main:app --reload
```

Server starts at: **http://localhost:8000**  
API Documentation: **http://localhost:8000/docs** ← Open this in your browser!

---

## 📋 Phase 5 — Database Migrations (Alembic)

After setting up the server, create the database tables:

```bash
# Initialize alembic (only once)
alembic init alembic

# Edit alembic/env.py — add these two lines after imports:
# from app.database import Base
# from app.modules.hr import models  # noqa

# Generate migration from your models
alembic revision --autogenerate -m "create hr tables"

# Apply migration (creates tables in PostgreSQL)
alembic upgrade head
```

---

## 🧪 Testing Your API

1. Open http://localhost:8000/docs
2. You'll see all available endpoints
3. Click **POST /auth/login** → Try it out → Enter email/password → Execute
4. Copy the `access_token` from the response
5. Click the **Authorize** 🔒 button at the top
6. Type: `Bearer <paste_your_token_here>` → Authorize
7. Now you can call protected endpoints!

---

## 📁 Project Structure

```
zoiko-one-backend/
├── app/
│   ├── main.py          ← Start here — app entry point
│   ├── config.py        ← Reads .env variables
│   ├── database.py      ← PostgreSQL connection
│   ├── core/
│   │   ├── security.py      ← Password hashing + JWT
│   │   ├── dependencies.py  ← get_current_user etc.
│   │   └── exceptions.py    ← Custom error responses
│   └── modules/
│       └── hr/
│           ├── models.py    ← Database table definitions
│           ├── schemas.py   ← Request/response validation
│           ├── service.py   ← Business logic
│           └── router.py    ← API endpoints
├── .env                 ← Your secrets (never push to GitHub!)
├── requirements.txt     ← Python packages
└── README.md
```

---

## 🔜 Next Modules to Build

Follow the same pattern (models → schemas → service → router) for:
- [ ] Zoiko Time    (`app/modules/time/`)
- [ ] Zoiko Payroll (`app/modules/payroll/`)
- [ ] Zoiko Billing (`app/modules/billing/`)
- [ ] Zoiko Comply  (`app/modules/comply/`)
- [ ] Zoiko Insights(`app/modules/insights/`)
