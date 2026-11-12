# Data dictionary

48 mapped SQLAlchemy models. Every model has an integer primary key and UTC created_at timestamp. Monetary integer columns are paisa. Foreign keys use RESTRICT deletion.

## AuditEvent (`audit_event`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| actor_id | INTEGER | True | user.id |
| action | VARCHAR(180) | False |  |
| entity | VARCHAR(180) | False |  |
| record_id | INTEGER | True |  |
| reason | VARCHAR(2000) | False |  |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: ForeignKeyConstraint(actor_id); PrimaryKeyConstraint(id)

## Carrier (`carrier`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| name | VARCHAR(80) | False |  |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: PrimaryKeyConstraint(id); UniqueConstraint(name)

## CaseAttachment (`case_attachment`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| request_id | INTEGER | False | return_request.id |
| actor_id | INTEGER | False | user.id |
| name | VARCHAR(180) | False |  |
| evidence | VARCHAR(4000) | False |  |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: ForeignKeyConstraint(request_id); PrimaryKeyConstraint(id); ForeignKeyConstraint(actor_id)

## CaseNote (`case_note`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| request_id | INTEGER | False | return_request.id |
| actor_id | INTEGER | False | user.id |
| body | VARCHAR(4000) | False |  |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: ForeignKeyConstraint(actor_id); ForeignKeyConstraint(request_id); PrimaryKeyConstraint(id)

## Customer (`customer`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| store_id | INTEGER | False | store.id |
| name | VARCHAR(180) | False |  |
| email | VARCHAR(180) | False |  |
| city | VARCHAR(180) | False |  |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: ForeignKeyConstraint(store_id); UniqueConstraint(store_id, email); PrimaryKeyConstraint(id)

## ExceptionResolution (`exception_resolution`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| exception_id | INTEGER | False | reconciliation_exception.id |
| actor_id | INTEGER | True | user.id |
| action | VARCHAR(180) | False |  |
| reason | VARCHAR(4000) | False |  |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: ForeignKeyConstraint(actor_id); ForeignKeyConstraint(exception_id); PrimaryKeyConstraint(id)

## ExchangeItem (`exchange_item`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| exchange_id | INTEGER | False | exchange_request.id |
| request_item_id | INTEGER | False | return_request_item.id |
| variant_id | INTEGER | False | product_variant.id |
| quantity | INTEGER | False | 1 |
| price_difference | INTEGER | False | 0 |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: quantity > 0; ForeignKeyConstraint(exchange_id); PrimaryKeyConstraint(id); ForeignKeyConstraint(request_item_id); ForeignKeyConstraint(variant_id); UniqueConstraint(exchange_id, request_item_id)

## ExchangeRequest (`exchange_request`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| request_id | INTEGER | False | return_request.id |
| status | VARCHAR(180) | False | approved |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: ForeignKeyConstraint(request_id); UniqueConstraint(request_id); PrimaryKeyConstraint(id)

## ImportBatch (`import_batch`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| actor_id | INTEGER | False | user.id |
| store_id | INTEGER | False | store.id |
| kind | VARCHAR(180) | False |  |
| filename | VARCHAR(180) | False |  |
| digest | VARCHAR(64) | False |  |
| status | VARCHAR(180) | False | preview |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: ForeignKeyConstraint(store_id); PrimaryKeyConstraint(id); ForeignKeyConstraint(actor_id)

## ImportColumnMapping (`import_column_mapping`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| batch_id | INTEGER | False | import_batch.id |
| source_column | VARCHAR(180) | False |  |
| target_column | VARCHAR(180) | False |  |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: ForeignKeyConstraint(batch_id); PrimaryKeyConstraint(id)

## ImportRow (`import_row`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| batch_id | INTEGER | False | import_batch.id |
| row_number | INTEGER | False |  |
| payload | JSON | False |  |
| status | VARCHAR(180) | False | pending |
| record_type | VARCHAR(180) | False |  |
| record_id | INTEGER | True |  |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: ForeignKeyConstraint(batch_id); PrimaryKeyConstraint(id); UniqueConstraint(batch_id, row_number)

## ImportRowError (`import_row_error`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| row_id | INTEGER | False | import_row.id |
| message | VARCHAR(2000) | False |  |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: PrimaryKeyConstraint(id); ForeignKeyConstraint(row_id)

## ItemDisposition (`item_disposition`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| inspection_id | INTEGER | False | item_inspection.id |
| action | VARCHAR(180) | False |  |
| quantity | INTEGER | False | 1 |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: ForeignKeyConstraint(inspection_id); PrimaryKeyConstraint(id); UniqueConstraint(inspection_id); quantity > 0

## ItemInspection (`item_inspection`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| receipt_item_id | INTEGER | False | warehouse_receipt_item.id |
| actor_id | INTEGER | False | user.id |
| result | VARCHAR(180) | False |  |
| note | VARCHAR(2000) | False |  |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: UniqueConstraint(receipt_item_id); ForeignKeyConstraint(receipt_item_id); PrimaryKeyConstraint(id); ForeignKeyConstraint(actor_id)

## OrderPayment (`order_payment`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| order_id | INTEGER | False | sales_order.id |
| reference | VARCHAR(180) | False |  |
| amount | INTEGER | False | 0 |
| method | VARCHAR(180) | False | COD |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: ForeignKeyConstraint(order_id); PrimaryKeyConstraint(id); UniqueConstraint(order_id, reference); amount >= 0

## Permission (`permission`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| name | VARCHAR(80) | False |  |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: PrimaryKeyConstraint(id); UniqueConstraint(name)

## Product (`product`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| store_id | INTEGER | False | store.id |
| name | VARCHAR(180) | False |  |
| category | VARCHAR(180) | False |  |
| archived | BOOLEAN | True | False |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: ForeignKeyConstraint(store_id); PrimaryKeyConstraint(id)

## ProductVariant (`product_variant`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| product_id | INTEGER | False | product.id |
| sku | VARCHAR(100) | False |  |
| name | VARCHAR(180) | False |  |
| price | INTEGER | False | 0 |
| archived | BOOLEAN | True | False |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: ForeignKeyConstraint(product_id); PrimaryKeyConstraint(id); price >= 0; UniqueConstraint(sku)

## ReconciliationException (`reconciliation_exception`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| store_id | INTEGER | False | store.id |
| request_id | INTEGER | True | return_request.id |
| payment_id | INTEGER | True | refund_payment.id |
| key | VARCHAR(180) | False |  |
| kind | VARCHAR(180) | False |  |
| status | VARCHAR(180) | False | open |
| expected | INTEGER | False | 0 |
| recorded | INTEGER | False | 0 |
| detail | VARCHAR(2000) | False |  |
| assigned_to | INTEGER | True | user.id |
| fingerprint | VARCHAR(180) | False |  |
| resolution_fingerprint | VARCHAR(180) | False |  |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: ForeignKeyConstraint(payment_id); ForeignKeyConstraint(store_id); ForeignKeyConstraint(request_id); PrimaryKeyConstraint(id); ForeignKeyConstraint(assigned_to); UniqueConstraint(key)

## ReconciliationMatch (`reconciliation_match`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| run_id | INTEGER | False | reconciliation_run.id |
| refund_id | INTEGER | False | refund.id |
| approved | INTEGER | False | 0 |
| paid | INTEGER | False | 0 |
| outstanding | INTEGER | False | 0 |
| overpaid | INTEGER | False | 0 |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: ForeignKeyConstraint(run_id); PrimaryKeyConstraint(id); ForeignKeyConstraint(refund_id)

## ReconciliationRun (`reconciliation_run`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| actor_id | INTEGER | True | user.id |
| store_id | INTEGER | True | store.id |
| exception_count | INTEGER | False | 0 |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: ForeignKeyConstraint(store_id); ForeignKeyConstraint(actor_id); PrimaryKeyConstraint(id)

## Refund (`refund`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| request_id | INTEGER | False | return_request.id |
| approved_amount | INTEGER | False | 0 |
| status | VARCHAR(180) | False | draft |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: UniqueConstraint(request_id); ForeignKeyConstraint(request_id); approved_amount >= 0; PrimaryKeyConstraint(id)

## RefundApproval (`refund_approval`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| refund_id | INTEGER | False | refund.id |
| actor_id | INTEGER | False | user.id |
| amount | INTEGER | False | 0 |
| reason | VARCHAR(2000) | False |  |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: ForeignKeyConstraint(refund_id); PrimaryKeyConstraint(id); ForeignKeyConstraint(actor_id)

## RefundLine (`refund_line`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| refund_id | INTEGER | False | refund.id |
| request_item_id | INTEGER | False | return_request_item.id |
| amount | INTEGER | False | 0 |
| description | VARCHAR(180) | False |  |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: UniqueConstraint(refund_id, request_item_id); ForeignKeyConstraint(refund_id); PrimaryKeyConstraint(id); amount >= 0; ForeignKeyConstraint(request_item_id)

## RefundPayment (`refund_payment`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| store_id | INTEGER | False | store.id |
| method_id | INTEGER | False | refund_payment_method.id |
| reference | VARCHAR(180) | False |  |
| amount | INTEGER | False | 0 |
| status | VARCHAR(180) | False | success |
| order_reference | VARCHAR(180) | False |  |
| source_row_id | INTEGER | True | import_row.id |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: ForeignKeyConstraint(source_row_id); UniqueConstraint(store_id, reference); amount > 0; ForeignKeyConstraint(store_id); PrimaryKeyConstraint(id); status IN ('pending','failed','success'); ForeignKeyConstraint(method_id)

## RefundPaymentAllocation (`refund_payment_allocation`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| payment_id | INTEGER | False | refund_payment.id |
| refund_id | INTEGER | False | refund.id |
| amount | INTEGER | False | 0 |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: UniqueConstraint(payment_id, refund_id); ForeignKeyConstraint(payment_id); PrimaryKeyConstraint(id); ForeignKeyConstraint(refund_id); amount > 0

## RefundPaymentMethod (`refund_payment_method`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| name | VARCHAR(80) | False |  |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: PrimaryKeyConstraint(id); UniqueConstraint(name)

## RefundPaymentReversal (`refund_payment_reversal`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| allocation_id | INTEGER | False | refund_payment_allocation.id |
| actor_id | INTEGER | False | user.id |
| reference | VARCHAR(180) | False |  |
| amount | INTEGER | False | 0 |
| reason | VARCHAR(2000) | False |  |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: UniqueConstraint(reference); amount > 0; ForeignKeyConstraint(allocation_id); PrimaryKeyConstraint(id); ForeignKeyConstraint(actor_id)

## ReplacementOrder (`replacement_order`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| exchange_id | INTEGER | False | exchange_request.id |
| reference | VARCHAR(180) | False |  |
| deadline | DATETIME | False |  |
| status | VARCHAR(180) | False | pending |
| difference_settled | BOOLEAN | True | False |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: UniqueConstraint(exchange_id); PrimaryKeyConstraint(id); UniqueConstraint(reference); ForeignKeyConstraint(exchange_id)

## ReplacementOrderItem (`replacement_order_item`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| replacement_id | INTEGER | False | replacement_order.id |
| exchange_item_id | INTEGER | False | exchange_item.id |
| quantity | INTEGER | False | 1 |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: UniqueConstraint(replacement_id, exchange_item_id); ForeignKeyConstraint(replacement_id); PrimaryKeyConstraint(id); ForeignKeyConstraint(exchange_item_id); quantity > 0

## ReplacementShipment (`replacement_shipment`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| replacement_id | INTEGER | False | replacement_order.id |
| carrier_id | INTEGER | False | carrier.id |
| tracking | VARCHAR(180) | False |  |
| status | VARCHAR(180) | False | dispatched |
| source_row_id | INTEGER | True | import_row.id |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: UniqueConstraint(replacement_id); ForeignKeyConstraint(replacement_id); ForeignKeyConstraint(carrier_id); PrimaryKeyConstraint(id); UniqueConstraint(tracking); ForeignKeyConstraint(source_row_id)

## ReplacementShipmentEvent (`replacement_shipment_event`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| shipment_id | INTEGER | False | replacement_shipment.id |
| status | VARCHAR(180) | False |  |
| note | VARCHAR(2000) | False |  |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: ForeignKeyConstraint(shipment_id); PrimaryKeyConstraint(id)

## ReturnApproval (`return_approval`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| request_id | INTEGER | False | return_request.id |
| actor_id | INTEGER | False | user.id |
| decision | VARCHAR(180) | False |  |
| reason | VARCHAR(2000) | False |  |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: PrimaryKeyConstraint(id); ForeignKeyConstraint(actor_id); ForeignKeyConstraint(request_id)

## ReturnReason (`return_reason`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| name | VARCHAR(180) | False |  |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: PrimaryKeyConstraint(id); UniqueConstraint(name)

## ReturnRequest (`return_request`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| order_id | INTEGER | False | sales_order.id |
| reason_id | INTEGER | False | return_reason.id |
| resolution | VARCHAR(40) | False |  |
| status | VARCHAR(40) | False | draft |
| reference | VARCHAR(80) | False |  |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: ForeignKeyConstraint(reason_id); ForeignKeyConstraint(order_id); PrimaryKeyConstraint(id); UniqueConstraint(reference)

## ReturnRequestItem (`return_request_item`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| request_id | INTEGER | False | return_request.id |
| order_item_id | INTEGER | False | sales_order_item.id |
| quantity | INTEGER | False | 1 |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: quantity > 0; ForeignKeyConstraint(request_id); PrimaryKeyConstraint(id); ForeignKeyConstraint(order_item_id); UniqueConstraint(request_id, order_item_id)

## ReturnStatusEvent (`return_status_event`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| request_id | INTEGER | False | return_request.id |
| actor_id | INTEGER | True | user.id |
| status | VARCHAR(180) | False |  |
| note | VARCHAR(2000) | False |  |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: ForeignKeyConstraint(request_id); PrimaryKeyConstraint(id); ForeignKeyConstraint(actor_id)

## Role (`role`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| name | VARCHAR(80) | False |  |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: UniqueConstraint(name); PrimaryKeyConstraint(id)

## RolePermission (`role_permission`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| role_id | INTEGER | False | role.id |
| permission_id | INTEGER | False | permission.id |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: ForeignKeyConstraint(permission_id); UniqueConstraint(role_id, permission_id); ForeignKeyConstraint(role_id); PrimaryKeyConstraint(id)

## SalesOrder (`sales_order`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| store_id | INTEGER | False | store.id |
| customer_id | INTEGER | False | customer.id |
| reference | VARCHAR(180) | False |  |
| status | VARCHAR(180) | False | paid |
| source_row_id | INTEGER | True | import_row.id |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: UniqueConstraint(store_id, reference); ForeignKeyConstraint(store_id); PrimaryKeyConstraint(id); ForeignKeyConstraint(customer_id); ForeignKeyConstraint(source_row_id)

## SalesOrderItem (`sales_order_item`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| order_id | INTEGER | False | sales_order.id |
| variant_id | INTEGER | False | product_variant.id |
| quantity | INTEGER | False | 1 |
| unit_price | INTEGER | False | 0 |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: quantity > 0 AND unit_price >= 0; ForeignKeyConstraint(order_id); PrimaryKeyConstraint(id); ForeignKeyConstraint(variant_id); UniqueConstraint(order_id, variant_id)

## Store (`store`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| name | VARCHAR(180) | False |  |
| platform | VARCHAR(40) | False | Shopify |
| archived | BOOLEAN | False | False |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: PrimaryKeyConstraint(id)

## StoreSetting (`store_setting`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| store_id | INTEGER | False | store.id |
| refund_days | INTEGER | False | 1 |
| replacement_days | INTEGER | False | 1 |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: UniqueConstraint(store_id); refund_days > 0 AND replacement_days > 0; ForeignKeyConstraint(store_id); PrimaryKeyConstraint(id)

## User (`user`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| email | VARCHAR(180) | False |  |
| name | VARCHAR(180) | False |  |
| password_hash | VARCHAR(255) | False |  |
| active | BOOLEAN | False | True |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: PrimaryKeyConstraint(id); UniqueConstraint(email)

## UserRole (`user_role`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| user_id | INTEGER | False | user.id |
| role_id | INTEGER | False | role.id |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: PrimaryKeyConstraint(id); ForeignKeyConstraint(user_id); UniqueConstraint(user_id, role_id); ForeignKeyConstraint(role_id)

## Warehouse (`warehouse`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| name | VARCHAR(180) | False |  |
| city | VARCHAR(180) | False |  |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: PrimaryKeyConstraint(id)

## WarehouseReceipt (`warehouse_receipt`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| request_id | INTEGER | False | return_request.id |
| warehouse_id | INTEGER | False | warehouse.id |
| reference | VARCHAR(180) | False |  |
| source_row_id | INTEGER | True | import_row.id |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: UniqueConstraint(reference); ForeignKeyConstraint(source_row_id); PrimaryKeyConstraint(id); ForeignKeyConstraint(warehouse_id); ForeignKeyConstraint(request_id)

## WarehouseReceiptItem (`warehouse_receipt_item`)

| Column | SQL type | Nullable | FK target / default |
|---|---|---|---|
| receipt_id | INTEGER | False | warehouse_receipt.id |
| request_item_id | INTEGER | False | return_request_item.id |
| quantity | INTEGER | False | 1 |
| condition | VARCHAR(180) | False |  |
| id | INTEGER | False |  |
| created_at | DATETIME | False | Application default (see models.py) |

Constraints: ForeignKeyConstraint(receipt_id); PrimaryKeyConstraint(id); ForeignKeyConstraint(request_item_id); UniqueConstraint(receipt_id, request_item_id); quantity > 0
