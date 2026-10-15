# Ghi chú kỹ thuật và nghiệp vụ

Chi tiết triển khai bằng tiếng Anh. Hướng dẫn cài đặt nằm trong [README.md](../README.md).

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
3. Staff sign in with an employee code and password. Responsible staff on an order remains a separate free-text field; status history does not yet attribute changes to the signed-in employee.
4. Phone numbers are required free text to support local/international formats. Optional email is syntax-validated. Profiles are not automatically deduplicated by name/phone; product catalogue maintenance is outside the UI.
5. Decimal quantities are allowed for kg, bunch, and box. No unit-specific rounding or maximum quantity has been agreed.
6. Small local datasets are loaded without pagination. Editing uses last-save-wins for concurrently edited fields; conflict-resolution screens are outside this prototype. Database transactions and safe numbering protect writes, but this is not a multi-user production deployment.

### Questions for the client

- Is this status sequence correct? Who can correct a mistaken status, and should delivered orders become read-only?
- Which customer fields, phone formats, product units, and quantity precision rules are needed?
- Should received dates or the customer linked to a saved order be editable?
- Should the responsible staff name and status history be linked to the signed-in employee, and are different staff permissions needed?
- Are name/phone duplicate warnings needed? Who should maintain the produce catalogue?
- Does “scheduled delivery” mean a calendar date only, and which business timezone should apply outside Vietnam?

### Deliberately outside scope

No product availability or inventory tracking; substitution preferences; recurring orders; delivery instructions; management summaries; payments; customer accounts; automated notifications. Evidence uploads, courier integrations, live shipment tracking, packing-time calculations, failed-delivery workflows, route optimisation, maps, and courier scheduling remain for future client discussion. Customer deletion is not implemented.

## Short manual demo

First sign in with the demo account below.

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


## Staff login

Open http://127.0.0.1:5173/login. Run `python -m app.seed` from `backend/` after updating the code, then restart the backend. This adds the authentication tables and the demo employee without resetting existing business records.

- Employee code: **NV001**
- Demo password: **Produce@123**
- Use **Sign Out** in the top bar to revoke the current session.

Employee codes are trimmed and case-insensitive; passwords are case-sensitive and their whitespace is preserved. Passwords are salted and hashed using PBKDF2-HMAC-SHA256 with 600,000 iterations. SQLite now also contains `employees` and `staff_sessions` tables. Session tokens are random; only their SHA-256 hashes are stored in SQLite. The browser receives an HttpOnly, SameSite=Strict cookie, limited to `/api`, with an eight-hour expiry. Refreshing or restarting the backend preserves an unexpired session. Signing out deletes it on the server.

API endpoints: `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout`. Login accepts `{"employee_code":"NV001","password":"Produce@123"}`. All mutating API requests, including login/logout, require the `X-Requested-With: ProduceDesk` header; the frontend supplies it automatically. Business endpoints return 401 without a valid session. The frontend redirects expired sessions to sign-in and returns users to the requested page after login. No password/token is stored in localStorage.

The local login limiter allows at most ten failed/in-flight attempts per client IP within five minutes; it is held in memory and resets when the backend restarts. This is a local demo account, not a production credential. Public deployment would require HTTPS with `COOKIE_SECURE=true`, private employee provisioning, and deployment-appropriate rate limiting. Staff registration, password recovery, role management, and audit attribution are not implemented in this update. Re-running seed never resets an existing employee password.
