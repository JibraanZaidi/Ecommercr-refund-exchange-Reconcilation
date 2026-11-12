"""Bounded CSV/XLSX adapters with mapping, durable row provenance and atomic confirmation."""
import csv, io, hashlib, zipfile
from openpyxl import load_workbook
from sqlalchemy.exc import IntegrityError
from .models import *
from .services import *

FIELDS={
 'orders':['order_reference','customer_name','customer_email','city','sku','product_name','category','quantity','unit_price','payment_reference'],
 'payments':['transaction_reference','amount','status','method','order_reference','refund_id'],
 'receipts':['receipt_reference','case_reference','sku','quantity','warehouse','condition','inspection','disposition'],
 'shipments':['replacement_reference','carrier','tracking'],
}

def parse_file(data, filename):
    if filename.lower().endswith('.csv'):
        try:
            reader=csv.DictReader(io.StringIO(data.decode('utf-8-sig')))
            if not reader.fieldnames or len(set(reader.fieldnames))!=len(reader.fieldnames): raise DomainError('Unique column headers required.')
            rows=list(reader)
        except (UnicodeDecodeError,csv.Error): raise DomainError('Use a UTF-8 CSV file.')
    elif filename.lower().endswith('.xlsx'):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                if sum(x.file_size for x in z.infolist())>30*1024*1024: raise DomainError('Uncompressed workbook exceeds 30 MB.')
            book=load_workbook(io.BytesIO(data),read_only=True,data_only=True)
            sheet=book.active
            if sheet.max_row and sheet.max_row>5001: raise DomainError('Maximum 5,000 rows per batch.')
            iterator=sheet.iter_rows(values_only=True); headers=[str(x or '').strip() for x in next(iterator)]
            if not all(headers) or len(set(headers))!=len(headers): raise DomainError('Unique non-empty column headers required.')
            rows=[dict(zip(headers,[str(v) if v is not None else '' for v in row])) for row in iterator if any(v is not None for v in row)]
            book.close()
        except DomainError: raise
        except Exception: raise DomainError('Unable to read XLSX workbook; upload a valid unencrypted file.')
    else: raise DomainError('Only .csv and .xlsx files are supported.')
    if not rows or len(rows)>5000: raise DomainError('Import must contain 1–5,000 data rows.')
    if any(None in row for row in rows): raise DomainError('CSV row has more cells than the header.')
    return [{str(k).strip():str(v or '').strip() for k,v in row.items()} for row in rows]

def preview(data, filename, kind, store_id, actor):
    if kind not in FIELDS: raise DomainError('Unknown import type.')
    get(Store,store_id)
    rows=parse_file(data,filename)
    batch=ImportBatch(actor_id=actor,store_id=store_id,kind=kind,filename=filename[:180],digest=hashlib.sha256(data).hexdigest())
    db.session.add(batch); db.session.flush()
    for i,row in enumerate(rows,2): db.session.add(ImportRow(batch_id=batch.id,row_number=i,payload=row))
    return batch

def mapped(row, mappings):
    return {target:str(row.payload.get(source,'')).strip() for target,source in mappings.items()}

def process(kind,d,store,actor,row_id):
    def required(key):
        v=d.get(key,'').strip()
        if not v: raise DomainError(f'{key}: value is required.')
        return v
    def named(model,key):
        x=model.query.filter_by(name=required(key)).first()
        if not x: raise DomainError(f'{key}: master record not found.')
        return x
    if kind=='payments':
        ref=required('transaction_reference'); value=money(required('amount')); status=required('status')
        old=RefundPayment.query.filter_by(store_id=store,reference=ref).first()
        method=named(RefundPaymentMethod,'method')
        if old:
            if (old.amount,old.status,old.method_id,old.order_reference)!=(value,status,method.id,d.get('order_reference','')): raise DomainError('Existing transaction reference has conflicting data.')
            if d.get('refund_id') and not any(a.refund_id==int(d['refund_id']) for a in old.allocations): raise DomainError('Existing payment allocation differs; review manually.')
            return old,True
        obj=record_payment(store,ref,required('amount'),status,method.id,actor,d.get('refund_id') or None,d.get('order_reference',''),row_id)
    elif kind=='orders':
        reference=required('order_reference'); sku=required('sku'); quantity=positive(required('quantity')); price=money(required('unit_price'))
        customer=Customer.query.filter_by(store_id=store,email=required('customer_email')).first()
        if not customer:
            customer=Customer(store_id=store,email=d['customer_email'],name=required('customer_name'),city=required('city')); db.session.add(customer); db.session.flush()
        variant=ProductVariant.query.filter_by(sku=sku).first()
        if not variant:
            product=Product(store_id=store,name=required('product_name'),category=required('category')); db.session.add(product); db.session.flush()
            variant=ProductVariant(product_id=product.id,sku=sku,name=product.name,price=price); db.session.add(variant); db.session.flush()
        if get(Product,variant.product_id).store_id!=store: raise DomainError('SKU belongs to a different store; use a store-prefixed SKU.')
        order=SalesOrder.query.filter_by(store_id=store,reference=reference).first()
        if not order:
            order=SalesOrder(store_id=store,customer_id=customer.id,reference=reference,source_row_id=row_id); db.session.add(order); db.session.flush()
        if order.customer_id!=customer.id: raise DomainError('Order reference conflicts with customer.')
        old=SalesOrderItem.query.filter_by(order_id=order.id,variant_id=variant.id).first()
        if old:
            if (old.quantity,old.unit_price)!=(quantity,price): raise DomainError('Existing order line differs; review order manually.')
            return order,True
        db.session.add(SalesOrderItem(order_id=order.id,variant_id=variant.id,quantity=quantity,unit_price=price))
        payref=required('payment_reference')+':'+sku
        db.session.add(OrderPayment(order_id=order.id,reference=payref,amount=quantity*price,method='Imported original payment'))
        obj=order
    elif kind=='receipts':
        case=ReturnRequest.query.join(SalesOrder).filter(ReturnRequest.reference==required('case_reference'),SalesOrder.store_id==store).first()
        if not case: raise DomainError('Case not found in selected store.')
        item=next((x for x in case.items if x.order_item.variant.sku==required('sku')),None)
        if not item: raise DomainError('SKU not part of the return.')
        ref=required('receipt_reference')+':'+required('sku'); quantity=positive(required('quantity'))
        old=WarehouseReceipt.query.filter_by(reference=ref).first()
        warehouse=named(Warehouse,'warehouse')
        if old:
            if old.request_id!=case.id or old.warehouse_id!=warehouse.id or old.items[0].quantity!=quantity or old.items[0].condition!=required('condition'): raise DomainError('Existing receipt conflicts with this row.')
            inspection=ItemInspection.query.filter_by(receipt_item_id=old.items[0].id).first()
            disposition=ItemDisposition.query.filter_by(inspection_id=inspection.id).first()
            if inspection.result!=required('inspection') or disposition.action!=required('disposition'): raise DomainError('Existing inspection conflicts with this row.')
            return old,True
        obj=receive(case,warehouse.id,ref,[(item.id,quantity,required('condition'),required('inspection'),required('disposition'))],actor,row_id)
    else:
        rep=ReplacementOrder.query.filter_by(reference=required('replacement_reference')).first()
        if not rep or get(ReturnRequest,get(ExchangeRequest,rep.exchange_id).request_id).order.store_id!=store: raise DomainError('Replacement not found in selected store.')
        carrier=named(Carrier,'carrier'); tracking=required('tracking')
        old=ReplacementShipment.query.filter_by(tracking=tracking).first()
        if old:
            if old.replacement_id!=rep.id or old.carrier_id!=carrier.id: raise DomainError('Tracking number conflicts with replacement/carrier.')
            return old,True
        obj=dispatch(rep,carrier.id,tracking,actor,row_id)
    db.session.flush(); return obj,False

def validate_batch(batch,mappings):
    if batch.status not in ('preview','validated'): raise DomainError('Batch already confirmed.')
    ImportColumnMapping.query.filter_by(batch_id=batch.id).delete()
    for target,source in mappings.items():
        if source: db.session.add(ImportColumnMapping(batch_id=batch.id,target_column=target,source_column=source))
    for row in batch.rows: ImportRowError.query.filter_by(row_id=row.id).delete()
    db.session.flush()
    errors=[]
    # Validate the whole batch in a savepoint, including intra-file duplicates.
    outer=db.session.begin_nested()
    for row in batch.rows:
        try:
            with db.session.begin_nested(): process(batch.kind,mapped(row,mappings),batch.store_id,batch.actor_id,row.id)
        except (DomainError,IntegrityError,ValueError,TypeError) as e: errors.append((row.id,str(e)[:1500] if not isinstance(e,IntegrityError) else 'Related record/unique constraint violation.'))
    outer.rollback()
    for row_id,error in errors: db.session.add(ImportRowError(row_id=row_id,message=error))
    batch.status='preview' if errors else 'validated'
    return errors

def confirm_batch(batch):
    if batch.status!='validated': raise DomainError('Validate the mapping successfully before confirming.')
    mappings={m.target_column:m.source_column for m in ImportColumnMapping.query.filter_by(batch_id=batch.id)}
    for row in batch.rows:
        obj,duplicate=process(batch.kind,mapped(row,mappings),batch.store_id,batch.actor_id,row.id)
        row.status='duplicate' if duplicate else 'imported'; row.record_type=type(obj).__name__; row.record_id=obj.id
    batch.status='confirmed'; audit(batch.actor_id,'confirm_import',batch); reconcile(batch.actor_id,batch.store_id)
