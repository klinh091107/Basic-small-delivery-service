# Produce Desk

A working local MVP for a small produce business. Staff can record customers and orders, edit existing orders, manually record progress, and view scheduled deliveries. All interface text is English.

**Stack:** React + Vite + plain CSS; Python + FastAPI; SQLite + SQLAlchemy; REST/JSON. The frontend reads and writes the real API. There is no localStorage data store, decorative login page, or frontend demo-data array.

## Quick start

Requirements: Python 3.11+ and Node.js 20.19+ (or 22.12+). Commands below are for macOS/Linux. Run from the project folder, using two terminals. Keep both servers running while using the application.

### Terminal 1 — database and backend

```bash
cd "/Users/klinh/github/PM gr project"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-lock.txt
cd backend
python -m app.seed
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

`requirements-lock.txt` contains the exact tested dependency versions. `requirements.txt` lists the direct dependency ranges for future intentional upgrades. On another machine, replace the first `cd` path with your checkout location.

### Terminal 2 — frontend

```bash
cd "/Users/klinh/github/PM gr project/frontend"
npm ci
npm run dev
```

- Website: **http://127.0.0.1:5173**
- Interactive FastAPI documentation: **http://127.0.0.1:8000/docs**
- OpenAPI JSON: **http://127.0.0.1:8000/openapi.json**

Vite proxies `/api` to `127.0.0.1:8000`, so browser requests use the same origin. Backend ports changed locally must also be updated in `frontend/vite.config.js`. The dev server uses a strict port to avoid accidentally opening another app.

Stop servers with Ctrl+C. Restarting them or refreshing the browser preserves all saved records. These servers bind to the local machine only. Authentication is outside this local demonstration; a real deployment requires staff authentication and access control.

## Database setup and demo data

- The default database is `backend/data/produce.db`. Its absolute path is resolved from the backend source directory, independently of the terminal working directory.
- Tables are created by backend startup or `python -m app.seed`. No separate database service is needed.
- The seed command stores **5 fictional customers, 10 products, and 10 orders** with two orders in each proposed status. It includes deliveries on today, tomorrow, and four days later.
- Seed dates use `Asia/Ho_Chi_Minh`. Form defaults use the browser's local calendar date. Audit timestamps are stored in UTC and displayed with an explicit UTC label.
- Seeding is idempotent, including after editing seeded records. SQLite's `PRAGMA user_version = 1` marks the demo dataset as initialized. Re-running the command leaves existing data and dates unchanged; it does not reset records or advance dates.
- To get a separate fresh dataset later, stop the backend and choose a **new** database file rather than deleting your existing records:

```bash
# From backend/, with the virtual environment activated:
export DATABASE_URL="sqlite:///$PWD/data/another-demo.db"
python -m app.seed
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Keep the environment variable for both seed and server commands. `DATABASE_URL` is optional, must use SQLite, and its parent directory must already exist. No `.env` loader is needed or included. The demo seed marker is not a schema migration system; future database migrations must account for it.

## Project structure

```text
backend/
  app/
    config.py       # One status sequence and allowed-transition configuration
    database.py     # SQLite engine, foreign-key enforcement, request sessions
    models.py       # Customer, Product, Order, OrderItem, OrderStatusHistory
    schemas.py      # Input validation and JSON response models
    services.py     # Transactional order creation and updates
    main.py         # REST routes and consistent error responses
    seed.py         # Idempotent persisted demo data
  tests/            # Isolated SQLite backend tests
  requirements.txt
  requirements-lock.txt
frontend/
  src/
    api.js          # Fetch, loading/error handling, calendar formatting
    components.jsx  # Shared tables, states, icons, and configuration context
    Customers.jsx   # Customer list, profile, editing, inline creation
    Orders.jsx      # Order list, creation, editing, and delivery schedule
    main.jsx        # Navigation and page routes
    styles.css      # Responsive plain CSS
  package.json
  package-lock.json
  vite.config.js
```

## Business behaviour and validation

- Creating a customer inside New Order saves that profile first. Saving the order then writes the order, all items, and the initial Received history event in **one database transaction**. A created customer remains in the directory if the subsequent order is cancelled or invalid.
- `ORD-000001` style numbers derive from the database-generated order ID. No row-count guessing or frontend numbering is used. The number is assigned before the transaction commits.
- Order updates save changed fields, replacement items, and any status-history event in one transaction. Failures roll back all changes, including item deletions already flushed within that transaction.
- PATCH updates only fields supplied in the request. A supplied `items` array replaces the entire item list; an omitted array preserves it. Explicit null is rejected for required fields. Customer email can be cleared with null.
- Frontend and backend reject blank required fields, no items, invalid products, duplicate product lines, nonpositive/nonfinite quantities, and delivery dates earlier than receipt. Decimal quantities are supported for all units in this prototype.
- Customer IDs must exist. Missing numeric record IDs return 404; malformed input returns 422; database integrity conflicts return 409.
- Changing the delivery address on an order never changes the customer profile. Editing a customer's saved address never changes delivery addresses on existing orders. Current customer contact details remain visible on linked orders.
- SQLite foreign keys, a unique order number, a unique product per order, and positive-quantity/date constraints provide database-level protection.
- Status names and transitions live only in `backend/app/config.py`. `/api/config` supplies the same configuration to the frontend. A changed configuration must remain compatible with existing stored statuses or include a data migration.
- Status counts use the same order-number/customer-name search as the order list, across all statuses. The active status filter narrows rows without hiding the other matching counts.
- Deliveries include all statuses, including Delivered. Date ranges are inclusive; omitting `date_to` means a single day. Rows sort by scheduled date, then numeric order ID (the sequence in the order number).
- Uncommitted form changes are discarded on Cancel/navigation. Saved records are authoritative; there is no autosave.

## REST API

Successful GET collections return JSON arrays, individual records return JSON objects, and creates return HTTP 201. Order responses include customer data; order details additionally include product lines and status history. Error responses consistently use:

```json
{
  "error": {
    "message": "Scheduled delivery date cannot precede received date.",
    "details": []
  }
}
```

Schema-validation errors include `field` and `message` entries in `details`.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/config` | Status names and allowed transitions |
| GET, POST | `/api/customers` | Search by `search` (name/phone), or create |
| GET, PATCH | `/api/customers/{id}` | View or update a profile |
| GET | `/api/customers/{id}/orders` | Customer's existing orders |
| GET | `/api/products?search=&category=` | Select-only produce catalogue |
| GET, POST | `/api/orders` | Filter by `search` and `status`, or create |
| GET | `/api/orders/status-counts?search=` | Counts for matching orders |
| GET, PATCH | `/api/orders/{id}` | View or edit an order |
| GET | `/api/deliveries?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD` | Inclusive delivery dates |

Static `/api/orders/status-counts` is declared before the dynamic order-ID route. Full request/response schemas and executable examples are provided by FastAPI `/docs`.

## Prototype assumptions — not confirmed client requirements

The draft's searchable catalogue, status filters/counts, received date, manually entered responsible staff name, customer/produce details, and manual packing/delivery progress are prototype assumptions for client review.

1. Proposed status flow: **Received → Packed → Handed to Courier → In Transit → Delivered**. Staff may keep the current status or advance one step. Skipped/backward changes are rejected; Delivered is terminal. No status is a courier confirmation.
2. Receipt date and the linked customer are fixed after creation. Scheduled delivery date, order-specific address, staff name, products, quantities, and status are editable, including on delivered orders for this demonstration.
3. Responsible staff is a free-text name, with no user identity/attribution system. Status history records previous/new values and UTC time, not a verified actor.
4. Phone numbers are required free text to support local/international formats. Optional email is syntax-validated. Profiles are not automatically deduplicated by name/phone; product catalogue maintenance is outside the UI.
5. Decimal quantities are allowed for kg, bunch, and box. No unit-specific rounding or maximum quantity has been agreed.
6. Small local datasets are loaded without pagination. Editing uses last-save-wins for concurrently edited fields; conflict-resolution screens are outside this prototype. Database transactions and safe numbering protect writes, but this is not a multi-user production deployment.

### Questions for the client

- Is this status sequence correct? Who can correct a mistaken status, and should delivered orders become read-only?
- Which customer fields, phone formats, product units, and quantity precision rules are needed?
- Should received dates or the customer linked to a saved order be editable?
- Is one responsible staff name enough, and what authentication/audit attribution is needed before deployment?
- Are name/phone duplicate warnings needed? Who should maintain the produce catalogue?
- Does “scheduled delivery” mean a calendar date only, and which business timezone should apply outside Vietnam?

### Deliberately outside scope

No product availability or inventory tracking; substitution preferences; recurring orders; delivery instructions; management summaries; payments; customer accounts; automated notifications. Evidence uploads, courier integrations, live shipment tracking, packing-time calculations, failed-delivery workflows, route optimisation, maps, and courier scheduling remain for future client discussion. Customer deletion is not implemented.

## Tests and frontend build

```bash
cd "/Users/klinh/github/PM gr project/backend"
../.venv/bin/python -m pytest -q

cd ../frontend
npm run build
```

Tests use separate temporary SQLite files, never the demo database. They cover creation/persistence, partial updates, item replacement, address independence, status rules/history, invalid inputs, transactional rollback (including injected write failures), status counts, delivery date/range filtering, customer/product endpoints, foreign keys, concurrent order-number generation, and seed idempotence after edits.

To serve the compiled frontend locally, keep the backend running and use:

```bash
npm run preview
```

Open http://127.0.0.1:4173. This preview also proxies `/api` to port 8000. `dist/` alone is not a full-stack deployment; the Python API and SQLite database must still run.

Frontend source formatting: `npx prettier --write src vite.config.js package.json index.html` (Prettier is a dev dependency). See [VERIFICATION.md](VERIFICATION.md) for the verification performed during implementation.

## Short manual demo

### 1. Record a customer and a produce order

1. Open Orders and click **New Order**.
2. Choose **New customer**. Enter a fictional name, phone, and address; leave email blank or enter a valid address. Click **Create Customer**.
3. Confirm the order delivery address is prefilled. Enter the responsible staff name and a delivery date on/after the received date.
4. In **Product 1**, type/select **Carrots**, quantity **2.5**. Click **Add Item**, choose **Coriander**, quantity **2**.
5. Click **Save Order**. Confirm the generated order number, Received status, initial history event, and success message. Return to Orders and search for the number/name; confirm the row and counts.

### 2. View and update an existing order

1. Open **View / Edit** for the saved order. Change the delivery date, order delivery address, staff name, and quantities; add/remove a product.
2. Set status to **Packed** and click **Save Changes**. Confirm success and the Received → Packed history event.
3. Open the customer profile. Confirm its address was not changed by editing the order. Edit the profile separately if desired and confirm existing order delivery addresses stay intact.
4. Refresh the browser, then stop/restart the backend and reopen the order. Confirm all saved changes remain.
5. Try two lines of the same product or quantity zero. Confirm a useful error and no saved partial change. The status selector only offers the current/next status; `/docs` can demonstrate server rejection of skipped/backward values.

### 3. View orders scheduled for delivery

1. Open **Deliveries**; today is selected by default.
2. Select the delivery date used above and click **Show Deliveries**. Confirm the order, phone, address, date, and current status.
3. Enable **Use date range**, choose an inclusive start/end, and apply. Confirm ordering by date then order number.
4. Choose a seeded delivery date containing Delivered orders (four days after initial seeding). Confirm they remain visible with the Delivered label. Open an order directly from the schedule.
