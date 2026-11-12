"""Transactional domain operations; caller commits or rolls back the entire operation."""
from datetime import timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4
from sqlalchemy import func
from .models import *

class DomainError(ValueError): pass

def money(value):
    try:
        d = Decimal(str(value).replace(',',''))
        if not d.is_finite() or d < 0 or d > Decimal('1000000000'): raise ValueError()
        return int((d * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError, TypeError): raise DomainError('Enter a non-negative PKR amount (maximum one billion).')

def positive(value):
    try:
        n = int(str(value))
        if n <= 0: raise ValueError()
        return n
    except (ValueError, TypeError): raise DomainError('Quantity must be a positive whole number.')

def get(model, ident):
    obj = db.session.get(model, int(ident))
    if not obj: raise DomainError(f'{model.__name__} record does not exist.')
    return obj

def audit(actor, action, obj, reason=''):
    db.session.flush()
    db.session.add(AuditEvent(actor_id=actor,action=action,entity=type(obj).__name__,record_id=obj.id,reason=reason))

def transition(case, status, actor, note):
    case.status = status
    db.session.add(ReturnStatusEvent(request_id=case.id,actor_id=actor,status=status,note=note))
    audit(actor,status,case,note)

def create_case(order, selected, reason_id, resolution, actor):
    if resolution not in ('refund','exchange'): raise DomainError('Choose refund or exchange.')
    get(ReturnReason, reason_id)
    if not selected: raise DomainError('Select at least one item.')
    case = ReturnRequest(order=order,reason_id=reason_id,resolution=resolution,reference='RET-'+uuid4().hex[:10].upper())
    db.session.add(case); db.session.flush()
    for item_id, quantity in selected:
        item = get(SalesOrderItem,item_id); quantity = positive(quantity)
        if item.order_id != order.id or quantity > item.quantity: raise DomainError('Invalid order item or quantity exceeds purchase.')
        db.session.add(ReturnRequestItem(case=case,order_item_id=item.id,quantity=quantity))
    transition(case,'draft',actor,'Return request created')
    return case

def approve_case(case, actor, reason):
    if case.status != 'draft': raise DomainError('Only draft requests may be approved.')
    if not reason.strip(): raise DomainError('Approval reason is required.')
    for line in case.items:
        used = db.session.query(func.coalesce(func.sum(ReturnRequestItem.quantity),0)).join(ReturnRequest).filter(
            ReturnRequestItem.order_item_id==line.order_item_id, ReturnRequest.status.in_(['approved','closed']),ReturnRequest.id!=case.id).scalar()
        if used+line.quantity > line.order_item.quantity: raise DomainError('Approved return quantities exceed the purchased quantity.')
    db.session.add(ReturnApproval(request_id=case.id,actor_id=actor,decision='approved',reason=reason))
    transition(case,'approved',actor,reason)
    if case.resolution=='exchange':
        exchange=ExchangeRequest(request_id=case.id); db.session.add(exchange); db.session.flush()
        for item in case.items:
            db.session.add(ExchangeItem(exchange_id=exchange.id,request_item_id=item.id,variant_id=item.order_item.variant_id,quantity=item.quantity,price_difference=0))

def approve_refund(case, value, actor, reason):
    if case.status!='approved' or case.resolution!='refund': raise DomainError('An approved refund return is required.')
    if Refund.query.filter_by(request_id=case.id).first(): raise DomainError('Refund already exists; use an audited payment/reversal.')
    value=money(value); maximum=sum(x.quantity*x.order_item.unit_price for x in case.items)
    if value<=0 or value>maximum: raise DomainError('Refund must be positive and cannot exceed returned merchandise value.')
    if not reason.strip(): raise DomainError('Approval reason is required.')
    refund=Refund(case=case,approved_amount=value,status='approved'); db.session.add(refund); db.session.flush()
    remaining=value
    for line in case.items:
        portion=min(remaining,line.quantity*line.order_item.unit_price); remaining-=portion
        db.session.add(RefundLine(refund_id=refund.id,request_item_id=line.id,amount=portion,description='Approved returned merchandise'))
    db.session.add(RefundApproval(refund_id=refund.id,actor_id=actor,amount=value,reason=reason)); audit(actor,'approve_refund',refund,reason)
    return refund

def balances(refund):
    paid=sum(a.amount-sum(r.amount for r in a.reversals) for a in refund.allocations if a.payment.status=='success')
    return {'approved':refund.approved_amount,'paid':paid,'outstanding':max(0,refund.approved_amount-paid),'overpaid':max(0,paid-refund.approved_amount)}

def allocate(payment, refund, value, actor):
    value=positive(value)
    if refund.status!='approved' or payment.store_id!=refund.case.order.store_id: raise DomainError('Store mismatch or unapproved refund.')
    if sum(a.amount for a in payment.allocations)+value>payment.amount: raise DomainError('Allocations exceed the payment amount.')
    if RefundPaymentAllocation.query.filter_by(payment_id=payment.id,refund_id=refund.id).first(): raise DomainError('Payment already allocated to this refund.')
    allocation=RefundPaymentAllocation(payment=payment,refund=refund,amount=value); db.session.add(allocation)
    audit(actor,'allocate_payment',payment,f'Refund {refund.id}; amount {value} paisa')
    return allocation

def record_payment(store_id, reference, value, status, method_id, actor, refund_id=None, order_reference='', source_row_id=None):
    get(Store,store_id); get(RefundPaymentMethod,method_id)
    reference=reference.strip(); value=money(value)
    if not reference or value<=0 or status not in ('pending','failed','success'): raise DomainError('Reference, positive amount and valid status are required.')
    if RefundPayment.query.filter_by(store_id=store_id,reference=reference).first(): raise DomainError('Transaction reference already recorded in this store.')
    p=RefundPayment(store_id=store_id,reference=reference,amount=value,status=status,method_id=method_id,order_reference=order_reference,source_row_id=source_row_id)
    db.session.add(p); db.session.flush()
    if refund_id: allocate(p,get(Refund,refund_id),value,actor)
    audit(actor,'record_payment',p); return p

def reverse(allocation, value, reference, actor, reason):
    value=money(value)
    if allocation.payment.status!='success': raise DomainError('Only successful payments can be reversed.')
    if value<=0 or value+sum(x.amount for x in allocation.reversals)>allocation.amount: raise DomainError('Reversal exceeds the unreversed allocated amount.')
    if not reference.strip() or not reason.strip(): raise DomainError('Unique reversal reference and reason are required.')
    reversal=RefundPaymentReversal(allocation=allocation,amount=value,reference=reference,actor_id=actor,reason=reason)
    db.session.add(reversal); audit(actor,'reverse_payment',reversal,reason)

def receive(case, warehouse_id, reference, lines, actor, source_row_id=None):
    if case.status!='approved': raise DomainError('Receive against an approved, open case.')
    get(Warehouse,warehouse_id)
    if not reference.strip() or not lines: raise DomainError('Receipt reference and item quantities are required.')
    receipt=WarehouseReceipt(case=case,warehouse_id=warehouse_id,reference=reference,source_row_id=source_row_id)
    db.session.add(receipt); db.session.flush()
    for item_id, quantity, condition, result, disposition in lines:
        line=get(ReturnRequestItem,item_id); quantity=positive(quantity)
        if line.request_id!=case.id: raise DomainError('Receipt item belongs to another case.')
        if condition not in ('sealed','opened','damaged') or result not in ('accepted','rejected') or disposition not in ('restock','quarantine','dispose'): raise DomainError('Invalid inspection choice.')
        # Physical over-receipts are preserved and reconciled, not silently discarded.
        ri=WarehouseReceiptItem(receipt=receipt,request_item_id=line.id,quantity=quantity,condition=condition)
        db.session.add(ri); db.session.flush()
        inspection=ItemInspection(receipt_item_id=ri.id,actor_id=actor,result=result,note='Receipt inspection')
        db.session.add(inspection); db.session.flush()
        db.session.add(ItemDisposition(inspection_id=inspection.id,action=disposition,quantity=quantity))
    audit(actor,'receive',receipt); return receipt

def create_replacement(case, variants, actor):
    exchange=ExchangeRequest.query.filter_by(request_id=case.id).first()
    if case.status!='approved' or not exchange: raise DomainError('Approved exchange required.')
    if ReplacementOrder.query.filter_by(exchange_id=exchange.id).first(): raise DomainError('Replacement already exists.')
    settings=StoreSetting.query.filter_by(store_id=case.order.store_id).first()
    replacement=ReplacementOrder(exchange_id=exchange.id,reference='EX-'+uuid4().hex[:10].upper(),deadline=now()+timedelta(days=settings.replacement_days if settings else 3))
    db.session.add(replacement); db.session.flush()
    for line in ExchangeItem.query.filter_by(exchange_id=exchange.id):
        variant=get(ProductVariant,variants.get(str(line.id),line.variant_id))
        if get(Product,variant.product_id).store_id!=case.order.store_id: raise DomainError('Replacement variant must belong to the order store.')
        line.variant_id=variant.id
        original=get(ReturnRequestItem,line.request_item_id)
        line.price_difference=(variant.price-original.order_item.unit_price)*line.quantity
        db.session.add(ReplacementOrderItem(replacement=replacement,exchange_item_id=line.id,quantity=line.quantity))
    replacement.difference_settled=all(x.price_difference==0 for x in ExchangeItem.query.filter_by(exchange_id=exchange.id))
    audit(actor,'create_replacement',replacement); return replacement

def dispatch(replacement, carrier_id, tracking, actor, source_row_id=None):
    if replacement.status!='pending': raise DomainError('Only a pending replacement can be dispatched.')
    if not tracking.strip(): raise DomainError('Tracking number is required.')
    get(Carrier,carrier_id)
    shipment=ReplacementShipment(replacement=replacement,carrier_id=carrier_id,tracking=tracking,source_row_id=source_row_id)
    db.session.add(shipment); db.session.flush(); replacement.status='dispatched'
    db.session.add(ReplacementShipmentEvent(shipment_id=shipment.id,status='dispatched',note='Handed to courier'))
    audit(actor,'dispatch',replacement); return shipment

def close_case(case, actor):
    if case.status!='approved': raise DomainError('Only approved cases can close.')
    for line in case.items:
        received=WarehouseReceiptItem.query.filter_by(request_item_id=line.id).all()
        if sum(x.quantity for x in received)!=line.quantity: raise DomainError('Received quantities must match approved quantities.')
        if any(not ItemInspection.query.filter_by(receipt_item_id=x.id,result='accepted').first() for x in received): raise DomainError('All receipts must pass inspection.')
    if case.resolution=='refund':
        if not case.refunds or any(balances(x)['outstanding'] or balances(x)['overpaid'] for x in case.refunds): raise DomainError('Refund must be fully settled with no overpayment.')
    else:
        exchange=ExchangeRequest.query.filter_by(request_id=case.id).first()
        replacement=ReplacementOrder.query.filter_by(exchange_id=exchange.id).first() if exchange else None
        if not replacement or replacement.status!='delivered' or not replacement.difference_settled: raise DomainError('Replacement must be delivered and price difference settled.')
    transition(case,'closed',actor,'Resolution conditions verified')

def reconcile(actor=None, store_id=None):
    run=ReconciliationRun(actor_id=actor,store_id=store_id); db.session.add(run); db.session.flush()
    findings={}
    def flag(key,kind,store,case=None,payment=None,expected=0,recorded=0,detail=''):
        findings[key]=dict(kind=kind,store_id=store,request_id=case,payment_id=payment,expected=expected,recorded=recorded,detail=detail)
    cases=ReturnRequest.query.join(SalesOrder).filter(ReturnRequest.status.in_(['approved','closed']))
    if store_id: cases=cases.filter(SalesOrder.store_id==store_id)
    for c in cases:
        sid=c.order.store_id
        for item in c.items:
            count=sum(x.quantity for x in WarehouseReceiptItem.query.filter_by(request_item_id=item.id))
            if count!=item.quantity: flag(f'receipt:{item.id}','missing_receipt' if count==0 else 'receipt_mismatch',sid,c.id,expected=item.quantity,recorded=count,detail='Item quantities; these values are units, not money.')
        if c.resolution=='refund':
            if not c.refunds: flag(f'approval:{c.id}','pending_refund_approval',sid,c.id,detail='Approved return has no approved refund.')
            for refund in c.refunds:
                b=balances(refund); db.session.add(ReconciliationMatch(run_id=run.id,refund_id=refund.id,**b))
                if b['outstanding']: flag(f'balance:{refund.id}','short_refund' if b['paid'] else 'pending_refund',sid,c.id,expected=b['approved'],recorded=b['paid'],detail='Net successful allocated payments are below approval.')
                settings=StoreSetting.query.filter_by(store_id=sid).first()
                if b['outstanding'] and refund.created_at+timedelta(days=settings.refund_days if settings else 7)<now():
                    flag(f'overdue_refund:{refund.id}','overdue_refund',sid,c.id,expected=b['approved'],recorded=b['paid'],detail='Store refund payment deadline exceeded.')
                if b['overpaid']:
                    flag(f'over:{refund.id}','overpayment',sid,c.id,expected=b['approved'],recorded=b['paid'],detail='Review excess net successful payment.')
                    if len([a for a in refund.allocations if a.payment.status=='success' and a.amount>sum(r.amount for r in a.reversals)])>1:
                        flag(f'duplicate:{refund.id}','potential_duplicate',sid,c.id,expected=b['approved'],recorded=b['paid'],detail='Separate successful transfers cause overpayment; valid installments alone are not duplicates.')
        else:
            ex=ExchangeRequest.query.filter_by(request_id=c.id).first()
            rep=ReplacementOrder.query.filter_by(exchange_id=ex.id).first() if ex else None
            if not rep: flag(f'exchange:{c.id}','missing_replacement',sid,c.id,detail='Approved exchange has no replacement order.')
            elif rep.status=='pending' and rep.deadline<now(): flag(f'late:{rep.id}','overdue_replacement',sid,c.id,detail=f'Dispatch deadline {rep.deadline:%Y-%m-%d} missed.')
    payments=RefundPayment.query
    if store_id: payments=payments.filter_by(store_id=store_id)
    for p in payments:
        allocated=sum(a.amount for a in p.allocations)
        if allocated<p.amount: flag(f'unmatched:{p.id}','unmatched_payment',p.store_id,payment=p.id,expected=p.amount,recorded=allocated,detail='Explicit authorized allocation required. Order text alone does not authorize a match.')
    existing=ReconciliationException.query
    if store_id: existing=existing.filter_by(store_id=store_id)
    by_key={x.key:x for x in existing}
    for key, data in findings.items():
        fingerprint=f"{data['kind']}:{data['expected']}:{data['recorded']}:{data['detail']}"
        e=by_key.get(key)
        if not e: e=ReconciliationException(key=key,**data); db.session.add(e)
        else:
            for field,value in data.items(): setattr(e,field,value)
            if e.status=='cleared' or (e.status=='resolved' and e.resolution_fingerprint!=fingerprint): e.status='open'
        e.fingerprint=fingerprint
    for key,e in by_key.items():
        if key not in findings and e.status!='cleared':
            e.status='cleared'; db.session.add(ExceptionResolution(exception_id=e.id,actor_id=actor,action='auto_clear',reason='Underlying discrepancy no longer exists.'))
    run.exception_count=len(findings); db.session.flush(); return run
