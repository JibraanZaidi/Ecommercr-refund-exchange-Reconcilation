"""Explicit relational domain model. All amounts are integer paisa (PKR × 100)."""
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, UniqueConstraint

db = SQLAlchemy()
def now(): return datetime.now(timezone.utc).replace(tzinfo=None)

class Base(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=now, nullable=False, index=True)

def fk(table, nullable=False):
    return db.Column(db.Integer, db.ForeignKey(table + '.id', ondelete='RESTRICT'), nullable=nullable, index=True)
def text(n=180, nullable=False, default=None):
    return db.Column(db.String(n), nullable=nullable, default=default)
def amount(): return db.Column(db.Integer, nullable=False, default=0)
def qty(): return db.Column(db.Integer, nullable=False, default=1)

class User(Base):
    email = db.Column(db.String(180), unique=True, nullable=False)
    name = text()
    password_hash = text(255)
    active = db.Column(db.Boolean, default=True, nullable=False)
    roles = db.relationship('Role', secondary='user_role', viewonly=True)
class Role(Base):
    name = db.Column(db.String(80), unique=True, nullable=False)
    permissions = db.relationship('Permission', secondary='role_permission', viewonly=True)
class Permission(Base):
    name = db.Column(db.String(80), unique=True, nullable=False)
class UserRole(Base):
    user_id = fk('user'); role_id = fk('role')
    __table_args__ = (UniqueConstraint('user_id','role_id'),)
class RolePermission(Base):
    role_id = fk('role'); permission_id = fk('permission')
    __table_args__ = (UniqueConstraint('role_id','permission_id'),)
class Store(Base):
    name = text(); platform = text(40, default='Shopify')
    archived = db.Column(db.Boolean, default=False, nullable=False)
class StoreSetting(Base):
    store_id = fk('store'); refund_days = qty(); replacement_days = qty()
    __table_args__ = (UniqueConstraint('store_id'), CheckConstraint('refund_days > 0 AND replacement_days > 0'),)
class AuditEvent(Base):
    actor_id = fk('user', True); action = text(); entity = text(); record_id = db.Column(db.Integer)
    reason = text(2000, default='')
class Customer(Base):
    store_id = fk('store'); name = text(); email = text(); city = text()
    __table_args__ = (UniqueConstraint('store_id','email'),)
class Product(Base):
    store_id = fk('store'); name = text(); category = text(); archived = db.Column(db.Boolean, default=False)
class ProductVariant(Base):
    product_id = fk('product'); sku = db.Column(db.String(100), unique=True, nullable=False)
    name = text(); price = amount(); archived = db.Column(db.Boolean, default=False)
    __table_args__ = (CheckConstraint('price >= 0'),)
class SalesOrder(Base):
    store_id = fk('store'); customer_id = fk('customer'); reference = text(); status = text(default='paid')
    source_row_id = fk('import_row', True)
    store = db.relationship('Store'); customer = db.relationship('Customer')
    items = db.relationship('SalesOrderItem', backref='order')
    cases = db.relationship('ReturnRequest', backref='order')
    __table_args__ = (UniqueConstraint('store_id','reference'),)
class SalesOrderItem(Base):
    order_id = fk('sales_order'); variant_id = fk('product_variant'); quantity = qty(); unit_price = amount()
    variant = db.relationship('ProductVariant')
    __table_args__ = (UniqueConstraint('order_id','variant_id'), CheckConstraint('quantity > 0 AND unit_price >= 0'),)
class OrderPayment(Base):
    order_id = fk('sales_order'); reference = text(); amount = amount(); method = text(default='COD')
    __table_args__ = (UniqueConstraint('order_id','reference'), CheckConstraint('amount >= 0'),)
class ReturnReason(Base):
    name = db.Column(db.String(180), unique=True, nullable=False)
class ReturnRequest(Base):
    order_id = fk('sales_order'); reason_id = fk('return_reason'); resolution = text(40)
    status = text(40, default='draft'); reference = db.Column(db.String(80), unique=True, nullable=False)
    items = db.relationship('ReturnRequestItem', backref='case')
    refunds = db.relationship('Refund', backref='case')
    receipts = db.relationship('WarehouseReceipt', backref='case')
    events = db.relationship('ReturnStatusEvent', backref='case', order_by='ReturnStatusEvent.created_at')
    reason = db.relationship('ReturnReason')
class ReturnRequestItem(Base):
    request_id = fk('return_request'); order_item_id = fk('sales_order_item'); quantity = qty()
    order_item = db.relationship('SalesOrderItem')
    __table_args__ = (UniqueConstraint('request_id','order_item_id'), CheckConstraint('quantity > 0'),)
class ReturnApproval(Base):
    request_id = fk('return_request'); actor_id = fk('user'); decision = text(); reason = text(2000)
class ReturnStatusEvent(Base):
    request_id = fk('return_request'); actor_id = fk('user', True); status = text(); note = text(2000)
class CaseNote(Base):
    request_id = fk('return_request'); actor_id = fk('user'); body = text(4000)
class CaseAttachment(Base):
    request_id = fk('return_request'); actor_id = fk('user'); name = text(); evidence = text(4000)
class Warehouse(Base):
    name = text(); city = text()
class WarehouseReceipt(Base):
    request_id = fk('return_request'); warehouse_id = fk('warehouse'); reference = db.Column(db.String(180), unique=True, nullable=False)
    source_row_id = fk('import_row', True)
    items = db.relationship('WarehouseReceiptItem', backref='receipt')
class WarehouseReceiptItem(Base):
    receipt_id = fk('warehouse_receipt'); request_item_id = fk('return_request_item'); quantity = qty(); condition = text()
    __table_args__ = (CheckConstraint('quantity > 0'), UniqueConstraint('receipt_id','request_item_id'),)
class ItemInspection(Base):
    receipt_item_id = fk('warehouse_receipt_item'); actor_id = fk('user'); result = text(); note = text(2000)
    __table_args__ = (UniqueConstraint('receipt_item_id'),)
class ItemDisposition(Base):
    inspection_id = fk('item_inspection'); action = text(); quantity = qty()
    __table_args__ = (UniqueConstraint('inspection_id'), CheckConstraint('quantity > 0'),)
class Refund(Base):
    request_id = fk('return_request'); approved_amount = amount(); status = text(default='draft')
    allocations = db.relationship('RefundPaymentAllocation', backref='refund')
    lines = db.relationship('RefundLine', backref='refund')
    __table_args__ = (UniqueConstraint('request_id'), CheckConstraint('approved_amount >= 0'),)
class RefundLine(Base):
    refund_id = fk('refund'); request_item_id = fk('return_request_item'); amount = amount(); description = text()
    __table_args__ = (UniqueConstraint('refund_id','request_item_id'), CheckConstraint('amount >= 0'),)
class RefundApproval(Base):
    refund_id = fk('refund'); actor_id = fk('user'); amount = amount(); reason = text(2000)
class RefundPaymentMethod(Base):
    name = db.Column(db.String(80), unique=True, nullable=False)
class RefundPayment(Base):
    store_id = fk('store'); method_id = fk('refund_payment_method'); reference = text(); amount = amount()
    status = text(default='success'); order_reference = text(default=''); source_row_id = fk('import_row', True)
    allocations = db.relationship('RefundPaymentAllocation', backref='payment')
    __table_args__ = (UniqueConstraint('store_id','reference'), CheckConstraint('amount > 0'), CheckConstraint("status IN ('pending','failed','success')"),)
class RefundPaymentAllocation(Base):
    payment_id = fk('refund_payment'); refund_id = fk('refund'); amount = amount()
    reversals = db.relationship('RefundPaymentReversal', backref='allocation')
    __table_args__ = (UniqueConstraint('payment_id','refund_id'), CheckConstraint('amount > 0'),)
class RefundPaymentReversal(Base):
    allocation_id = fk('refund_payment_allocation'); actor_id = fk('user'); reference = db.Column(db.String(180), unique=True, nullable=False)
    amount = amount(); reason = text(2000)
    __table_args__ = (CheckConstraint('amount > 0'),)
class ExchangeRequest(Base):
    request_id = fk('return_request'); status = text(default='approved')
    __table_args__ = (UniqueConstraint('request_id'),)
class ExchangeItem(Base):
    exchange_id = fk('exchange_request'); request_item_id = fk('return_request_item'); variant_id = fk('product_variant'); quantity = qty(); price_difference = amount()
    __table_args__ = (UniqueConstraint('exchange_id','request_item_id'), CheckConstraint('quantity > 0'),)
class ReplacementOrder(Base):
    exchange_id = fk('exchange_request'); reference = db.Column(db.String(180), unique=True, nullable=False)
    deadline = db.Column(db.DateTime, nullable=False); status = text(default='pending'); difference_settled = db.Column(db.Boolean, default=False)
    items = db.relationship('ReplacementOrderItem', backref='replacement')
    shipments = db.relationship('ReplacementShipment', backref='replacement')
    __table_args__ = (UniqueConstraint('exchange_id'),)
class ReplacementOrderItem(Base):
    replacement_id = fk('replacement_order'); exchange_item_id = fk('exchange_item'); quantity = qty()
    __table_args__ = (UniqueConstraint('replacement_id','exchange_item_id'), CheckConstraint('quantity > 0'),)
class Carrier(Base):
    name = db.Column(db.String(80), unique=True, nullable=False)
class ReplacementShipment(Base):
    replacement_id = fk('replacement_order'); carrier_id = fk('carrier'); tracking = db.Column(db.String(180), unique=True, nullable=False)
    status = text(default='dispatched'); source_row_id = fk('import_row', True)
    __table_args__ = (UniqueConstraint('replacement_id'),)
class ReplacementShipmentEvent(Base):
    shipment_id = fk('replacement_shipment'); status = text(); note = text(2000)
class ImportBatch(Base):
    actor_id = fk('user'); store_id = fk('store'); kind = text(); filename = text(); digest = text(64); status = text(default='preview')
    rows = db.relationship('ImportRow', backref='batch')
class ImportColumnMapping(Base):
    batch_id = fk('import_batch'); source_column = text(); target_column = text()
class ImportRow(Base):
    batch_id = fk('import_batch'); row_number = db.Column(db.Integer, nullable=False); payload = db.Column(db.JSON, nullable=False)
    status = text(default='pending'); record_type = text(default=''); record_id = db.Column(db.Integer)
    __table_args__ = (UniqueConstraint('batch_id','row_number'),)
class ImportRowError(Base):
    row_id = fk('import_row'); message = text(2000)
class ReconciliationRun(Base):
    actor_id = fk('user', True); store_id = fk('store', True); exception_count = amount()
class ReconciliationMatch(Base):
    run_id = fk('reconciliation_run'); refund_id = fk('refund'); approved = amount(); paid = amount(); outstanding = amount(); overpaid = amount()
class ReconciliationException(Base):
    store_id = fk('store'); request_id = fk('return_request', True); payment_id = fk('refund_payment', True)
    key = db.Column(db.String(180), unique=True, nullable=False); kind = text(); status = text(default='open')
    expected = amount(); recorded = amount(); detail = text(2000); assigned_to = fk('user', True)
    fingerprint = text(default=''); resolution_fingerprint = text(default='')
class ExceptionResolution(Base):
    exception_id = fk('reconciliation_exception'); actor_id = fk('user', True); action = text(); reason = text(4000)
