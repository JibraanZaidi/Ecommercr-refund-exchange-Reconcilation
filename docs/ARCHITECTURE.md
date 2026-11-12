# Architecture and viva guide

The project is a server-rendered Flask application, not a live Shopify/WooCommerce integration. Merchants export data and map it into documented flat-row import contracts. SQLite is appropriate for the semester demonstration and a controlled single-merchant pilot; all demo stores share one staff workspace. Store filters are operational filters, not tenant security boundaries.

## Request lifecycle

1. `wsgi.py` loads environment settings and calls the factory in `app/__init__.py`.
2. Flask-WTF checks CSRF on every POST, including login and logout.
3. `views.load_user` resolves the session user. `access` and `can` enforce permissions on the server.
4. Views parse input and call `services.py` or `imports.py` for business rules.
5. Related writes commit together. Exceptions roll back; successful POSTs redirect to GET.
6. Jinja templates extend `base.html`. Shared macros render forms, pagination and filters.

## Why separate models?

Orders have many purchased lines. A return selects a quantity of specific lines. Each returned line can arrive through multiple receipt lines. A refund has calculation lines and an approval record. A payment has one or more explicit allocations; reversals belong to allocations, so the accounting effect is unambiguous. An exchange has replacement lines and a shipment/event history. Provenance points operational imports back to the source row and file batch.

Roles and permissions use many-to-many association models. The seeded Admin is an all-permission administrator. Other roles receive one domain permission: support, warehouse or accounts. Role memberships can be assigned by Admin on the Users screen; permission definitions are deliberately not editable through arbitrary forms.

## Exact accounting

Store money as integer paisa: PKR 2,500 = 250000. Parse user input with Decimal and ROUND_HALF_UP to two decimal places. Values are bounded to PKR one billion per input. Display divisions by 100 are for presentation only; reconciliations sum integers.

Net paid = sum of successful allocations minus their recorded reversals.
Outstanding = max(approved minus net paid, 0).
Overpaid = max(net paid minus approved, 0).
Pending and failed transactions do not contribute. A reversal cannot exceed an allocation's remaining net amount. Allocation totals cannot exceed payment value and cannot cross stores. An extra successful transfer is a potential duplicate only when multiple net-positive transfers collectively exceed approval; an exact installment settlement is valid.

## Matching and idempotency

Orders are unique by store + order reference. Payment references are unique per store. Product SKUs use a unique store-prefixed catalog identifier. Warehouse import receipt identities combine source receipt reference + SKU. Each replacement has one shipment in this semester scope. Multiple receipt dates are supported; split replacement shipments are not.

No payment is silently matched using order text. An explicit refund ID in the import or an authorized manual allocation is required. Conflicting repetitions are errors. Identical repetitions are skipped and retained as duplicate import rows.

Validation executes the full batch in a nested transaction and rolls it back, then persists row errors. Confirmation rechecks records and commits the entire batch atomically. Imports are capped at 5,000 rows / 8 MB; larger merchant exports should be split. Excel decompressed-size checks bound archive expansion.

Each reconciliation discrepancy has a stable unique key. Unchanged reruns update the same record; absent findings become cleared. A manual resolution suppresses the same finding until the underlying fingerprint changes. A reviewer can reopen it. Reconciliation is manual via button/CLI and runs automatically after operational actions; it is not a scheduled background job.

## State and deletion policy

| Record | Allowed operations |
|---|---|
| Unapproved return | Create, read, edit quantities/reason/resolution; delete; cancel; approve |
| Approved/closed return | Read, append notes/evidence; fulfill; close only after conditions pass; no destructive delete |
| Refund | Create approved calculation and approval history; read; settle through payments/reversals; approval is immutable |
| Payment | Record/read; pending → success/failed; explicit allocation; successful allocation reversal |
| Warehouse receipt | Append/read with inspection/disposition; discrepancies remain for review; no history-erasing edits |
| Replacement | Create/read; pending → dispatched → delivered; accounts records price-difference settlement evidence |
| Imported original order | Append lines/read; conflicting source corrections require review rather than overwriting evidence |
| Unused master record | Create/read/update/delete; FK constraints block deletion when used |
| Stores/products/variants | Also archive/unarchive |
| User | Create/edit role/password/name; deactivate/reactivate; cannot deactivate or demote yourself |
| Store settings | Create/read/update; no delete |
| Audit/import/reconciliation history | Append/read; no delete UI |

A physical warehouse over-receipt is recorded as evidence and flagged, rather than silently truncated. Closing requires exact receipt quantities and accepted inspections, as well as a settled refund or delivered replacement with settled price difference.

## Viva questions

- **Factory?** Creates independently configurable application instances for local use and isolated tests.
- **Blueprint?** Groups web routes independently from app initialization.
- **Session vs cookie?** Signed session stores user ID; a separate harmless cookie stores page size. Database lookup verifies the current active user on each request.
- **CSRF?** Token ties state-changing requests to a browser session. It supplements authentication and authorization.
- **Foreign key?** Guarantees a referenced parent exists. SQLite enforcement is explicitly enabled on every connection.
- **PRG?** Redirect after POST prevents accidental browser refresh resubmission.
- **ORM?** Parameterized ORM queries map Python entities to relational rows and avoid interpolated SQL.
- **Why separate refund/payment?** One refund can be paid in installments; one payment can be explicitly distributed across refunds of the same store.
- **Why not delete posted records?** Reversals and transitions preserve evidence and audit history.
- **Tests?** Isolated temporary SQLite database with realistic seeded records; service tests and authenticated HTTP requests verify both calculations and access control.

## Pilot boundaries

No live banking, storefront API sync, emailed notifications, binary evidence attachments or automatic courier lookups. Evidence is stored as text references/notes. Refund calculations cover merchandise only; tax, shipping and discounts must be incorporated into an agreed import/calculation policy before a real pilot. Replacement price differences are recorded with an Accounts evidence note, not collected by this app. UTC timestamps are used throughout.

Before public deployment: use a production WSGI server, HTTPS and production cookie mode; replace demo accounts and secret, establish backups, add login rate limiting and operational monitoring, and evaluate write concurrency and tenant/store access requirements. SQLite checks and transactions are appropriate for the demo but this is not a multi-tenant banking system. The default Flask development server is local-only.
