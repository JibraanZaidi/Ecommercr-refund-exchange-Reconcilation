# E-commerce Refund & Exchange Reconciliation System

**ReturnLedger** is a Flask semester application for matching original orders, return requests, warehouse receipts, refund payment evidence and replacement shipments. Python + Flask + Flask-SQLAlchemy + Jinja2 + SQLite, with responsive sage/ivory CSS and lightweight progressive JavaScript.

## Quick start — Windows PowerShell

Requires Python 3.11 or later. Extract the ZIP, open PowerShell inside `refund_reconcile`, then run:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
$secret = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
(Get-Content .env) -replace '^SECRET_KEY=.*', "SECRET_KEY=$secret" | Set-Content .env
.\.venv\Scripts\python.exe -m flask --app wsgi init-db
.\.venv\Scripts\python.exe -m flask --app wsgi seed
.\.venv\Scripts\python.exe -m flask --app wsgi verify-schema
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m flask --app wsgi run
```

Open http://127.0.0.1:5000. Using the virtual environment's Python directly avoids PowerShell activation-policy issues. `init-db` preserves existing data; `seed` is repeatable and skips existing users. Stop the server with Ctrl+C.

## macOS / Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
# Set a fresh random SECRET_KEY in .env before running.
.venv/bin/python -m flask --app wsgi init-db
.venv/bin/python -m flask --app wsgi seed
.venv/bin/python -m flask --app wsgi verify-schema
.venv/bin/python -m pytest -q
.venv/bin/python -m flask --app wsgi run
```

For the exact dependency set used in verification, install with `-r requirements-lock.txt` instead of `-r requirements.txt`.

## Demo accounts

All four fictional accounts use **DemoPass!2026**. Use only in a local demonstration.

| Role | Email | Write access |
|---|---|---|
| Admin | admin@demo.local | All modules, users, master data and settings |
| Customer Support | support@demo.local | Orders, return drafts/approvals, notes, evidence, replacements, closure |
| Warehouse | warehouse@demo.local | Receipts/inspection, shipment dispatch and delivery |
| Accounts | accounts@demo.local | Refund approval, payment evidence, allocations, reversals, exception review, reports |

All staff can view the shared operational workspace. This is not multi-tenant isolation. Warehouse cannot approve refunds even by posting directly to the URL.

## Included functionality

- 48 explicit mapped models and 48 physical tables, foreign keys enabled, exact integer-paisa accounting.
- Database KPIs with store/date filters, exception and refund activity charts, linked drilldowns.
- Multiple stores with overlapping order references; item-level partial returns; draft edit/delete; audited approval and closure.
- Split receipts, condition, inspection and disposition; quantity discrepancies stay visible.
- Approved refunds, installments, pending/failed/successful payments, explicit allocations and partial reversals.
- Replacement SKU selection, price-difference evidence, dispatch deadline, tracking and delivery.
- Stable reconciliation exception keys, auto-clear, assignment, evidence notes, manual resolution and reopening.
- CSV/XLSX upload, mapping, preview, row errors, atomic confirmation, replay detection and provenance.
- Master CRUD, protected deletes, archive/deactivate actions, session login, CSRF, pagination and page-size cookie.
- Filtered CSV/XLSX exports and audit trail.

The seeded first refund is Rs. 2,500 approved, Rs. 2,000 paid, Rs. 500 outstanding. Import `samples/payments-installment.csv` for Store 1 to settle it. This sample assumes a fresh seed. Two stores, 16 orders and 16 cases demonstrate food, skincare, haircare and herbal products. Other cases include missing receipts, failed/reversed/unmatched payments, overpayment and overdue exchange.

## Project map

```text
app/
  __init__.py       Factory, SQLite setup, CSRF, error pages
  models.py         48 explicit domain models
  services.py       Refund, return, receipt, exchange and reconciliation rules
  imports.py        File parsing, preview, mapping, validation, confirmation
  views.py          Authenticated routes, permissions, forms, CRUD and exports
  seed.py           Fictional seed and CLI commands
  templates/       Jinja inheritance, macros and operational screens
  static/          Responsive CSS and small progressive-enhancement script
tests/             Domain and HTTP acceptance tests
samples/           Ready-to-use fictional CSV/XLSX examples and blank templates
docs/              Architecture/viva, ERD, data dictionary, rubric, walkthrough
wsgi.py            Entrypoint
requirements.txt   Direct dependency pins
requirements-lock.txt Exact dependency versions used for verification
.env.example       Environment template
```

## Dates, filters and reconciliations

Dates are stored and displayed in UTC. Start/end filters include the full end date. Case/refund activity filters use the return case creation date; exception lists/reports use exception creation date; order and payment lists use their own creation date. Dashboard figures and their drilldowns follow the same corresponding date basis. Reports show units for warehouse quantity discrepancies and PKR for money discrepancies.

Reconciliation runs after related workflow changes, after confirmed imports, from the Accounts button or with:

```powershell
.\.venv\Scripts\python.exe -m flask --app wsgi reconcile
```

It is not scheduled automatically. Outstanding is approved minus net successful allocations, clamped at zero; overpayment is separate. The refund payment deadline and replacement dispatch deadline are configurable per store in Master data & settings.

## Documentation

- [Architecture and viva guide](docs/ARCHITECTURE.md)
- [All-model data dictionary](docs/DATA_DICTIONARY.md)
- [Grouped ER diagrams](docs/ERD.md)
- [Import mapping guide](docs/IMPORT_GUIDE.md)
- [Semester demo walkthrough](docs/DEMO_WALKTHROUGH.md)
- [Rubric checklist](docs/RUBRIC_CHECKLIST.md)
- [Actual verification results](docs/VERIFICATION.md)

## Scope

A runnable semester implementation and starting point for a controlled merchant pilot. No live storefront, bank or courier connection is required or included. Imports use documented flat-row contracts, not universal native-export parsers. Refund approval is capped to returned merchandise value; tax, shipping and discount allocation require an agreed policy before use with real merchant accounts. Binary evidence uploads are not included: use evidence reference text. Each replacement has one shipment; return receipts can arrive in multiple deliveries. Fonts use Google Fonts when available, with local system fallbacks. See the architecture guide for production hardening and scope limits.
