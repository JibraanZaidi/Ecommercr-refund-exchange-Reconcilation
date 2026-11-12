# MASTER PROMPT — E-COMMERCE REFUND & EXCHANGE RECONCILIATION SYSTEM

Act as a senior Flask developer, SQLAlchemy database architect, software tester, and professional UI/UX designer.

Build a complete Web Engineering semester project named **E-commerce Refund & Exchange Reconciliation System**.

The system is for Shopify and WooCommerce merchants who need to match order records, warehouse returns, refund payments, and replacement shipments. It must help customer support, warehouse staff, and accounts teams identify what is pending, what amount remains payable, and which records need manual review.

Build a working Flask application that can be demonstrated with realistic fictional data and used as the starting point for a real merchant pilot.

## Mandatory instructor requirements

Follow the supplied Flask Project Rubric exactly.

Use Python, Flask, Flask-SQLAlchemy, Jinja2, and SQLite. Keep Flask as the backend and Jinja2 as the server-rendered frontend. Use CSS and lightweight JavaScript where needed.

The project is graded on:

1. Project Setup & Structure — 10 marks
2. Routing & View Functions — 15 marks
3. Templates & Jinja2 — 15 marks
4. Database Integration & CRUD — 20 marks
5. Forms, Validation, Cookies & Sessions — 15 marks
6. Code Quality & Organization — 10 marks
7. Functionality & Testing — 10 marks
8. Documentation — 5 marks

**CRITICAL: The database must contain at least 40 meaningful, related SQLAlchemy models backed by actual SQLite tables. This is a hard requirement.**

## Project modules

### 1. Management Dashboard

Show database-backed KPI cards for open return cases, approved refunds awaiting payment, total outstanding refund amount, potential duplicate payments, overdue exchanges, and unresolved reconciliation exceptions.

Include date and store filters, charts for refund activity and exception types, and tables for cases that need action. Link each KPI to its filtered detail list.

### 2. Stores, Customers & Original Orders

Manage stores, customers, products, variants, orders, order items, and original payment records. Support multiple stores so the same order number can exist in different stores.

Provide order search by order number, customer, SKU, or transaction reference. An order detail page must show its original items, return requests, receipts, refunds, and exchanges together.

### 3. CSV & Excel Imports

Support `.csv` and `.xlsx` imports for:

- Shopify and WooCommerce order data through documented sample column mappings.
- Warehouse return receipts and received item quantities.
- Refund payment or bank transfer records.
- Replacement shipment records and tracking numbers.

Provide sample files, a preview before confirmation, column mapping, validation errors with row numbers, and import history. Preserve the source file name and row reference for imported records. Re-importing the same records must avoid creating duplicates. Provide a manual entry option for each operational record type.

### 4. Return Requests & Warehouse Inspection

Create a return request against an existing order and select individual order items and quantities. Record the return reason, requested resolution, approval, warehouse receipt, received condition, inspection result, and item disposition.

Support partial returns, multiple items in one case, and separate receipts for items that arrive on different dates. Prevent active approved return quantities from exceeding the original purchased quantity. Show a case timeline from request through resolution.

### 5. Refund Management

Record the refund calculation, approved amount, approval history, payment method, transaction reference, and payment status. Support full refunds, partial refunds, and a refund paid through multiple transactions.

Show approved, successfully paid, and outstanding amounts separately. Handle pending, failed, and reversed payments. Allow authorized users to review and resolve payment discrepancies with a reason and an audit trail.

The semester application records and reconciles refund payments. Use demo transactions and imported records, with no live bank or payment gateway required.

### 6. Exchange & Replacement Management

Create replacement orders linked to approved exchange requests. Record the returned item, replacement variant, quantity, and any applicable price difference. Track fulfillment, courier tracking number, dispatch, and delivery.

Flag approved exchanges without a replacement order and replacement orders that miss their dispatch deadline. Require the recorded resolution conditions to be met before closing the case.

### 7. Reconciliation & Exception Management

Reconcile original orders, return requests, warehouse receipts, approved refunds, successful payments, and replacement shipments.

- Use store plus order reference to identify an order. Use payment references and explicit allocations to link payments to approved refunds.
- Flag unmatched or ambiguous records for manual review. Give staff enough information to verify and link records.
- Detect missing warehouse receipts, receipt quantity mismatches, pending refunds, short refunds, overpayments, potential duplicate refunds, unmatched payments, and overdue replacements.
- Treat repeated imports of the same transaction as import duplicates. Flag separate successful transactions as potential duplicate payments when the evidence warrants review. Multiple valid installments must remain supported.
- Calculate outstanding refund as the approved amount minus net successful payments allocated to that refund, after reversals. Show any overpayment separately. Pending and failed payments must not reduce the outstanding amount.
- Allow authorized staff to assign an exception, add notes, record evidence, and resolve or reopen it with a reason.
- Re-running reconciliation against unchanged data must not create duplicate open exceptions.

### 8. Reports & Exports

Provide date-range and store filters for outstanding refunds, payment discrepancies, unmatched records, overdue exchanges, warehouse receipt discrepancies, and return reasons by product.

Export filtered results to CSV or Excel. Include order number, case reference, status, relevant amounts, and the reason for each exception.

### 9. User Roles, Audit Logs & Settings

Implement at least four roles: Admin, Customer Support, Warehouse, and Accounts.

Enforce permissions on the server. Customer Support manages requests and case notes. Warehouse records receipts and inspections. Accounts manages refund approval, payments, and financial exceptions. Admin manages users, roles, stores, and settings.

Record important actions with the actor, timestamp, record, and reason where applicable. Allow store-level configuration for refund and replacement deadlines.

## Database

Create at least 40 mapped SQLAlchemy models with meaningful foreign keys, appropriate uniqueness constraints, and actual use in the application. This suggested model inventory may be adapted if the final application meets the minimum and all workflows remain complete:

- **Access and settings:** User, Role, Permission, UserRole, RolePermission, Store, StoreSetting, AuditEvent.
- **Orders and catalog:** Customer, Product, ProductVariant, SalesOrder, SalesOrderItem, OrderPayment.
- **Returns and warehouse:** ReturnReason, ReturnRequest, ReturnRequestItem, ReturnApproval, ReturnStatusEvent, CaseNote, CaseAttachment, Warehouse, WarehouseReceipt, WarehouseReceiptItem, ItemInspection, ItemDisposition.
- **Refunds:** Refund, RefundLine, RefundApproval, RefundPaymentMethod, RefundPayment, RefundPaymentAllocation, RefundPaymentReversal.
- **Exchanges:** ExchangeRequest, ExchangeItem, ReplacementOrder, ReplacementOrderItem, Carrier, ReplacementShipment, ReplacementShipmentEvent.
- **Imports and reconciliation:** ImportBatch, ImportColumnMapping, ImportRow, ImportRowError, ReconciliationRun, ReconciliationMatch, ReconciliationException, ExceptionResolution.

Use appropriate SQLAlchemy relationships, indexes, and database constraints. Enable SQLite foreign-key enforcement. Store money in integer minor units or use another exact representation with a documented rounding policy. Scope order identifiers, matching rules, and transaction uniqueness to the relevant store or source.

Implement full CRUD for applicable master data and editable business records. Allow deletion of eligible drafts and unused master records. Use archival, cancellation, reversal, or status transitions for finalized records that need an audit history. Document which operations apply to each module.

Include a command or automated test that verifies the number of physical tables and mapped models after database initialization.

## Flask requirements

- Use an application factory, Blueprints, an organized project structure, and clear view functions.
- Use GET for read operations and POST for state changes.
- Use dynamic routes with integer converters where appropriate.
- Use SQLAlchemy ORM queries and paginate large lists.
- Use Jinja2 template inheritance with `extends`, `blocks`, and reusable macros or partials.
- Validate all forms on the server and display clear field errors.
- Implement session-based login and logout, secure password hashing, role checks, CSRF protection, and flash messages.
- Use the Post-Redirect-Get pattern for successful form submissions.
- Demonstrate cookies with a harmless preference such as table page size. Use secure session cookie settings appropriate to local and production environments.
- Add searchable tables, status and date filters, custom error pages, and clear empty states.
- Keep reconciliation and import logic in testable Python modules. Use database transactions for related updates.

## UI DESIGN — IMPORTANT

Create a premium, responsive operations dashboard with forest sage green, soft ivory, muted olive, charcoal typography, and subtle gold accents.

Use **Manrope** for headings and **DM Sans** for interface text, with appropriate fallbacks.

Include:

- A professional sidebar and compact top navigation.
- Clickable KPI cards, charts, and clear status badges.
- Filterable tables with useful row actions.
- Clean forms and a step-by-step import screen.
- An order and case detail page with a timeline, related records, and payment totals.
- A side-by-side view of the expected and recorded amounts on discrepancy detail pages.
- Subtle hover and sidebar transitions that respect reduced-motion preferences.

Avoid neon colors, excessive gradients, flashy animations, heavy shadows, and overcrowded layouts. Every button, filter, navigation item, and form must have a working purpose.

## Demo data and acceptance tests

Provide a repeatable seed command and realistic fictional Pakistani e-commerce data in PKR. Include two stores, role-based demo users, and sample orders for food, skincare, haircare, and herbal products. Use fictional names and transaction references.

Demonstrate and test these cases:

1. An approved Rs. 2,500 refund with Rs. 2,000 paid shows Rs. 500 outstanding.
2. A second valid installment of Rs. 500 settles the refund and clears the short-payment exception.
3. Re-importing the same refund file creates no duplicate payment records.
4. A separate successful transfer that causes an overpayment appears for review.
5. A failed payment does not reduce the outstanding balance, and a reversal restores the relevant balance.
6. An ambiguous payment record remains unmatched until authorized staff review it.
7. A partial return updates only the affected line quantities.
8. An approved exchange without a replacement order is flagged. Once created, the replacement can be tracked through dispatch and delivery.
9. A warehouse user cannot approve a refund, including through a direct POST request.
10. Dashboard totals and exports match the underlying filtered records.

Test login, CSRF handling, role permissions, CRUD operations, import validation, reconciliation calculations, state transitions, and key routes. Run the test suite and fix failures before final delivery.

## Documentation

Provide:

- `requirements.txt` with compatible dependency versions.
- `README.md` and `.env.example`.
- Windows PowerShell setup commands for creating a virtual environment, installing dependencies, configuring the app, initializing and seeding SQLite, starting the server, and running tests.
- Demo login credentials for each role.
- An ER diagram and a data dictionary covering all implemented models.
- Sample CSV and Excel templates with a column-mapping guide.
- A short viva guide explaining the architecture, relationships, sessions, validation, and reconciliation logic.
- A rubric compliance checklist mapped to concrete files, routes, or tests.
- A short semester demo walkthrough from file import through exception resolution.

## Final delivery

Generate the complete runnable source code in an organized folder and provide a ZIP of the project. Include templates, static assets, tests, sample import files, and documentation.

Verify installation from a clean environment, initialize and seed the database, and report the actual model count and test results. Include the Windows PowerShell commands in the final handoff.

Deliver the working application, with no placeholder screens or dummy buttons. Keep the code understandable for a BS Artificial Intelligence student who needs to explain it in a university viva.