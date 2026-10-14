# Verification — 15 October 2026 (Vietnam time)

## Automated checks

- `cd backend && ../.venv/bin/python -m pytest -q`: **47 passed**.
- `cd frontend && npm run build`: **passed**, production assets generated in `frontend/dist/`.
- `npm run preview`: compiled frontend loaded the saved 11 orders through the real API in a fresh Chrome tab; no browser console warnings/errors were recorded in that session.
- `python -m app.seed`: successfully initialized the local SQLite database. Re-running after browser edits preserved records and dates.
- HTTP check: Vite returned 200 and proxied `/api/orders/status-counts` to the running FastAPI backend. The initial dataset returned 10 orders, two in every status.

The backend suite uses temporary database files and tests order creation, IDs generated safely during concurrent creates, persistence through a new engine connection, partial PATCH semantics, item replacement, status progression, address independence, validation, static route ordering, customer/product endpoints, date filtering, seed idempotence, and database foreign keys. It also injects database errors after writes have begun to verify complete transaction rollback.

One non-failing dependency warning remains: Starlette's TestClient warns that its `httpx` integration is deprecated in favour of `httpx2`. The pinned `httpx` version still runs all 47 tests successfully. No application warnings were suppressed.

## Browser checks against the real API

Tested in Chrome with the local frontend and FastAPI/SQLite backend:

- Orders loaded the 10 persisted seed records and matching status counts.
- Created a fictional customer within New Order; the new customer was selected and their saved address prefilled the order address.
- Attempted duplicate product lines; the form showed the explicit duplicate-product error.
- Created `ORD-000011` with two products and a decimal quantity; the detail page opened and displayed the initial Received event.
- Updated the delivery date using the native date input, order-specific address, staff member, and quantity; advanced Received → Packed. Success and the timestamped history appeared.
- Reloaded the page and confirmed the updated values remained.
- Opened the customer profile, verified its original address, then edited the profile independently. The order retained its own delivery address.
- Searched by customer name; one matching order appeared with Packed = 1 and other status counts = 0.
- Selected tomorrow's delivery date; the saved order appeared with its phone, order address, and Packed status.
- Applied an inclusive date range containing later seeded deliveries; Delivered orders remained visible, sorted after earlier scheduled dates.
- Stopped and restarted the actual backend process, reopened the order, and confirmed its edited values persisted.
- Attempted quantity zero; the form focused the visible error and prevented saving.
- Removed an item, added a different product with quantity 1.25, and saved the replacement item list.

## Responsive and accessibility checks

- Visually inspected the desktop Orders page and order detail form.
- Tested a 390 × 844 viewport for the delivery schedule and order editor. Fixed an overflow caused by visually hidden table labels escaping their scroll container; document width now equals the viewport width.
- Tables scroll within their own focusable, labelled regions; the page itself does not overflow horizontally at the tested width.
- Inputs have labels, statuses include text, buttons/links are keyboard controls, native date inputs support keyboard editing, and custom validation errors receive focus.
- Loading, saved-success, and invalid-input states were observed during the browser walkthrough.

This is a functional manual accessibility check, not a formal WCAG audit. Safari, Firefox, physical mobile devices, screen readers, and deployment beyond localhost were not tested.

## Local demo records

Browser testing intentionally left fictional records for inspection: `Demo QA Customer`, `Demo Workflow Customer`, and `ORD-000011`. The current local database therefore has 7 customers, 10 products, and 11 orders. A fresh database seeded using the README starts with the original 5 customers and 10 orders. No real customer data was used.

No remote deployment was performed. The temporary development/preview servers were stopped after verification. This deliverable is the requested local Python/SQLite demonstration; run commands and limitations are in the README.
