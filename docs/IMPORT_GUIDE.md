# Import mapping guide

Use Import center: choose store + record type, upload CSV/XLSX, map columns, validate, inspect row-numbered errors, then confirm. No operational records are committed during preview. Confirm commits the entire batch. Source filename, source row number, raw row payload, mapping and result remain available in import history.

UTF-8 CSV with header row; Excel first worksheet with header row; one row per order SKU, receipt SKU, payment or shipment. Dates are ingestion timestamps in this version. Do not concatenate stores in one batch. Price/amount columns are **PKR decimal**, not paisa. IDs are application IDs visible in the relevant ledger/details.

## Orders: required columns

`order_reference, customer_name, customer_email, city, sku, product_name, category, quantity, unit_price, payment_reference`

Shopify-style export mapping:

| Source column | Application column |
|---|---|
| Name | order_reference |
| Billing Name | customer_name |
| Email | customer_email |
| Shipping City | city |
| Lineitem sku | sku |
| Lineitem name | product_name |
| Product Type (enrichment) | category |
| Lineitem quantity | quantity |
| Lineitem price | unit_price |
| Payment Reference | payment_reference |

WooCommerce-style export mapping:

| Source column | Application column |
|---|---|
| Order Number | order_reference |
| Customer Name | customer_name |
| Billing Email | customer_email |
| Shipping City | city |
| SKU | sku |
| Item Name | product_name |
| Category | category |
| Quantity | quantity |
| Item Unit Price | unit_price |
| Transaction ID | payment_reference |

Export headers vary by plugin/report. These are documented example adapters, not a claim that every native export has these exact columns. Fill down order/customer details on every item row. Aggregate repeated identical SKUs within an order into one row. Supply missing category or COD payment reference before importing. For multiple stores, prefix SKU identifiers consistently (e.g. S1-001 / S2-001).

Order imports create missing customers/products/variants and add missing order lines; conflicting existing quantity/price values require manual source review. Original payment reference is suffixed with SKU to represent per-line original payment evidence without double counting a repeated full-order payment.

## Payments

`transaction_reference, amount, status, method, order_reference, refund_id`

Required: transaction_reference, positive amount, status (`success`, `pending`, `failed`), method (existing master name, e.g. `Bank transfer`). Optional: order_reference (informational), refund_id (explicit allocation). Blank refund_id remains unmatched even if the order text looks plausible. The same store/reference with different amount/status/method/order reference is a validation conflict; pending status can be updated through the payment screen, never by overwrite import.

## Receipts

`receipt_reference, case_reference, sku, quantity, warehouse, condition, inspection, disposition`

All required. Case must be approved and belong to selected store. Warehouse must exist. Condition: sealed/opened/damaged. Inspection: accepted/rejected. Disposition: restock/quarantine/dispose. Use a new receipt reference for a different arrival. Multiple rows under one source receipt use distinct SKUs; application identity is source reference + SKU.

## Shipments

`replacement_reference, carrier, tracking`

All required. Existing pending replacement in the selected store and existing carrier name. Import records dispatch. Confirm delivery from the case screen as Warehouse. Re-import identical tracking does not duplicate it.

## Samples

- `payments-installment.csv/.xlsx`: Store 1, refund ID 1, Rs. 500 final installment after fresh seed.
- `payments-unmatched.csv/.xlsx`: intentionally blank refund ID for manual review.
- `orders.csv/.xlsx`: new fictional order for Store 1.
- `receipts.csv/.xlsx` and `shipments.csv/.xlsx`: use the references from the freshly seeded database; the generated sample data is synchronized with seed output.
- `*-template.csv/.xlsx`: blank templates, also available from Import center.

A rejected batch remains in preview with errors. Fix values in the source file and upload a new batch. Mapping errors alone can be corrected and revalidated in the existing batch. CSV and Excel report exports neutralize formula-prefixed text cells.
