# FreshRoute Produce Delivery

An website for produce business staff to manage customers, create and edit orders, update order progress, and view scheduled deliveries. The interface is in English.

## 1. Prerequisites

- Python **3.11 or later**, with `pip` and `venv`.
- Node.js **22.12 or later**, with npm.
- An Internet connection to download dependencies during initial setup.

The commands below are for **macOS/Linux**. Download or clone the source code, then open a terminal in the project root—the folder containing `backend/` and `frontend/`.

Check your installed tools:

```bash
python3 --version
node --version
npm --version
```

SQLite runs through Python, so no separate database server is required. The default configuration does not require a `.env` file.

## 2. Install and Run the Backend

In the **first terminal**, start from the project root:

```bash
# Create and activate a Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install backend dependencies using the tested versions
python -m pip install -r backend/requirements-lock.txt

# Create the database, sample data, and demo account
cd backend

# Start the API server
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Keep this terminal running. The database is created at `backend/data/produce.db`. The initial seed adds **5 customers, 10 products, 10 orders, and 1 demo employee account**. Running the seed again does not duplicate records or reset an existing account's password.

## 3. Install and Run the Frontend

Open a **second terminal** in the project root:

```bash
cd frontend
npm ci
npm run dev
```

Keep both terminals running, then open **http://127.0.0.1:5173**.

| Demo login | Value |
| --- | --- |
| Employee code | `NV001` |
| Password | `Produce@123` |

Sign in, then use **New Order** to create an order, **Orders** to view/edit orders and update their status, and **Deliveries** to view the delivery schedule. Use **Sign Out** to log out.

Press `Ctrl+C` in each terminal to stop the servers. Saved data remains in the SQLite file.

## 5. Tests and Build

Start from the project root:

```bash
# Run backend tests with temporary databases, preserving demo data
cd backend
../.venv/bin/python -m pytest -q

# Test frontend validation and build
cd ../frontend
node --test src/validation.test.js
npm run build

# Preview the build at http://127.0.0.1:4173
npm run preview
```

