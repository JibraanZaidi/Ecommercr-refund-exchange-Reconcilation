# Verification report

Verified 12 November 2026 (Pakistan client date) in a fresh Python 3.12 virtual environment on Linux.

| Check | Actual result |
|---|---|
| Dependency installation | Clean venv installation from `requirements-lock.txt` succeeded |
| Source isolation | Clean source copy excluded database, .env, caches and virtual environments |
| Database initialization | `flask --app wsgi init-db` succeeded |
| Demo seeding | `flask --app wsgi seed` succeeded |
| Mapped SQLAlchemy models | **48** |
| Physical SQLite tables | **48** |
| SQLite foreign keys | Enabled and asserted by test |
| Final complete test suite | **51 passed in 40.07 seconds** |
| Python parsing/compilation | All application and test files parsed; application compiled |
| HTTP templates | Login, dashboard, operational lists/details/forms, master screens, reports and templates returned expected responses |
| Browser visual verification | Not completed: local Chromium launch blocked by environment socket restrictions |
| Windows execution | Commands provided; execution performed on Linux, not a Windows host |

## Tested behavior

- Rs. 2,500 approval with Rs. 2,000 paid leaves Rs. 500 outstanding.
- Rs. 500 valid installment settles it and automatically clears short-payment exception.
- Repeated CSV payment import creates no additional payment; conflicting repetition produces an error.
- Extra successful transfer produces overpayment and potential duplicate review.
- Pending/failed payment exclusion; successful allocation reversals restore balances and reject excessive reversal.
- Ambiguous payment stays unmatched until explicit allocation; cross-store allocation is rejected.
- Partial returns preserve original purchased quantities; cumulative approved quantity cannot exceed purchase.
- Exchange without replacement is flagged; creating replacement clears it; shipment import, dispatch, delivery and closure work.
- Warehouse direct POST refund approval returns 403; support cannot mutate master data.
- Dashboard outstanding total equals the filtered CSV export sum; invalid dates rejected.
- Login/logout, failed login, CSRF missing/valid tokens, protected routes and secure password login behavior.
- Master create/update/delete, referenced-delete protection, user role assignment and deactivation.
- Draft edit/delete with audit evidence; manual receipt, notes and evidence.
- All four import types, identical repeat detection, Excel parser, mapping/confirmation HTTP flow and atomic validation rollback.
- Split receipts, over-receipt discrepancy, inspection requirements and close-case guards.
- Exception resolve/reopen and unchanged-run suppression; refund deadline setting.
- Page-size preference cookie and spreadsheet formula neutralization.

## Reproduce

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m flask --app wsgi init-db
.\.venv\Scripts\python.exe -m flask --app wsgi seed
.\.venv\Scripts\python.exe -m flask --app wsgi verify-schema
.\.venv\Scripts\python.exe -m pytest -q
```

Tests create isolated temporary SQLite databases and do not modify the demonstration database. Test timings depend on the computer. The included implementation is a semester/pilot starting point; operational limits and production requirements are documented in ARCHITECTURE.md.
