import io,csv,re
import pytest
from sqlalchemy import inspect,text as sql_text
from app.models import *
from app.services import *
from app.imports import *
from conftest import login

def first_refund(): return Refund.query.order_by(Refund.id).first()
def actor(): return User.query.filter_by(email='accounts@demo.local').first().id

def test_physical_schema_and_foreign_keys(app):
    assert len(db.Model.registry.mappers)>=40
    assert len(inspect(db.engine).get_table_names())==len(db.Model.registry.mappers)
    assert db.session.execute(sql_text('PRAGMA foreign_keys')).scalar()==1

def test_partial_installment_and_idempotent_reconcile(app):
    r=first_refund(); assert balances(r)['approved']==250000
    assert balances(r)['paid']==200000 and balances(r)['outstanding']==50000
    reconcile(actor()); db.session.flush(); count=ReconciliationException.query.count()
    reconcile(actor()); db.session.flush(); assert ReconciliationException.query.count()==count
    record_payment(r.case.order.store_id,'VALID-INSTALLMENT',500,'success',1,actor(),r.id)
    db.session.flush(); reconcile(actor()); db.session.commit()
    assert balances(r)['outstanding']==0
    assert ReconciliationException.query.filter_by(key=f'balance:{r.id}').one().status=='cleared'
    assert not ReconciliationException.query.filter_by(key=f'duplicate:{r.id}',status='open').first()

def test_overpayment_flag(app):
    r=first_refund(); record_payment(r.case.order.store_id,'EXTRA-TRANSFER',600,'success',1,actor(),r.id)
    db.session.flush(); reconcile(actor()); db.session.commit()
    assert balances(r)['overpaid']==10000
    assert ReconciliationException.query.filter_by(key=f'duplicate:{r.id}',status='open').one()

def test_failed_pending_and_reversal(app):
    r=first_refund()
    for status in ('failed','pending'): record_payment(1,status,500,status,1,actor(),r.id)
    db.session.flush(); assert balances(r)['outstanding']==50000
    a=r.allocations[0]; reverse(a,100,'REV-TEST',actor(),'Bank reversal'); db.session.flush()
    assert balances(r)['outstanding']==60000
    with pytest.raises(DomainError): reverse(a,3000,'TOO-LARGE',actor(),'Excess')

def test_import_repeat_and_conflict(app):
    data=b'transaction_reference,amount,status,method,order_reference,refund_id\nIMP-1,500,success,Bank transfer,ORD-1001,1\n'
    for _ in range(2):
        b=preview(data,'refunds.csv','payments',1,actor()); db.session.flush()
        assert validate_batch(b,{f:f for f in FIELDS['payments']})==[]
        confirm_batch(b); db.session.commit()
    assert RefundPayment.query.filter_by(reference='IMP-1').count()==1
    assert b.rows[0].status=='duplicate'
    b=preview(data.replace(b',500,',b',600,'),'changed.csv','payments',1,actor()); db.session.flush()
    assert validate_batch(b,{f:f for f in FIELDS['payments']})
    assert b.status=='preview'

def test_unmatched_requires_explicit_allocation(app):
    p=record_payment(1,'AMBIGUOUS',100,'success',1,actor(),order_reference='ORD-1001')
    db.session.flush(); reconcile(actor()); db.session.commit()
    assert not p.allocations
    assert ReconciliationException.query.filter_by(payment_id=p.id,kind='unmatched_payment',status='open').one()
    allocate(p,first_refund(),10000,actor()); db.session.flush(); reconcile(actor()); db.session.commit()
    assert ReconciliationException.query.filter_by(payment_id=p.id,kind='unmatched_payment').one().status=='cleared'

def test_partial_return_and_over_return_prevention(app):
    order=SalesOrder.query.first(); item=order.items[0]
    assert item.quantity==2 and order.cases[0].items[0].quantity==1
    c=create_case(order,[(item.id,1)],1,'refund',actor()); db.session.flush(); approve_case(c,actor(),'Second item returned'); db.session.flush()
    c2=create_case(order,[(item.id,1)],1,'refund',actor()); db.session.flush()
    with pytest.raises(DomainError): approve_case(c2,actor(),'Too many')
    assert item.quantity==2

def test_exchange_dispatch_delivery(app):
    c=ReturnRequest.query.filter_by(resolution='exchange').first()
    assert ReconciliationException.query.filter_by(key=f'exchange:{c.id}',status='open').one()
    rep=create_replacement(c,{},actor()); db.session.flush(); reconcile(actor())
    assert ReconciliationException.query.filter_by(key=f'exchange:{c.id}').one().status=='cleared'
    ship=dispatch(rep,1,'TRACK-TEST',actor()); db.session.flush()
    assert rep.status=='dispatched' and ship.status=='dispatched'

def test_warehouse_cannot_approve_refund_direct_post(app,client):
    login(client,'warehouse')
    assert client.post('/cases/1/refund',data={'amount':'2500','reason':'unauthorized'}).status_code==403
    assert client.get('/payments').status_code==403
    assert client.post('/reconcile').status_code==403

def test_login_and_logout(app,client):
    assert client.get('/orders').status_code==302
    assert b'incorrect' in client.post('/login',data={'email':'admin@demo.local','password':'wrong'}).data
    assert login(client).status_code==200
    assert client.post('/logout').status_code==302
    assert client.get('/').status_code==302

def test_csrf_enforced(app,client):
    app.config['WTF_CSRF_ENABLED']=True
    assert client.post('/login',data={'email':'admin@demo.local','password':'DemoPass!2026'}).status_code==400
    html=client.get('/login').data.decode(); token=re.search(r'name="csrf_token" value="([^"]+)"',html).group(1)
    assert client.post('/login',data={'csrf_token':token,'email':'admin@demo.local','password':'DemoPass!2026'}).status_code==302
    assert client.post('/logout').status_code==400

@pytest.mark.parametrize('path',['/','/orders','/orders/1','/orders/new','/cases','/cases/1','/cases/1/refund','/refunds','/payments','/payments/new','/exceptions','/exceptions/1','/imports','/reports','/settings/stores','/settings/users','/audit','/samples/payments.csv','/samples/receipts.xlsx'])
def test_key_routes(app,client,path):
    login(client); response=client.get(path); assert response.status_code==200

def test_master_crud_and_permissions(app,client):
    login(client)
    client.post('/settings/reasons',data={'name':'New reason'})
    r=ReturnReason.query.filter_by(name='New reason').one()
    client.post(f'/settings/reasons/{r.id}',data={'name':'Updated reason'})
    assert r.name=='Updated reason'
    client.post(f'/settings/reasons/{r.id}',data={'action':'delete'})
    assert db.session.get(ReturnReason,r.id) is None
    client.post('/logout'); login(client,'support')
    assert client.post('/settings/reasons',data={'name':'Forbidden'}).status_code==403

def test_filters_dashboard_export_agree(app,client):
    login(client)
    expected=sum(balances(r)['outstanding'] for r in Refund.query.join(ReturnRequest).join(SalesOrder).filter(SalesOrder.store_id==1).all())
    html=client.get('/?store=1').data.decode()
    assert f'Rs. {expected/100:,.2f}' in html
    response=client.get('/reports?report=outstanding&store=1&format=csv')
    rows=list(csv.DictReader(io.StringIO(response.data.decode())))
    assert sum(money(r['Outstanding PKR']) for r in rows)==expected
    assert client.get('/reports?start=invalid').status_code==400

def test_close_requires_receipts_and_balance(app):
    c=first_refund().case
    with pytest.raises(DomainError): close_case(c,actor())
    record_payment(1,'SETTLE',500,'success',1,actor(),first_refund().id); db.session.flush()
    close_case(c,actor()); assert c.status=='closed'

def test_import_validation_row_errors_atomic(app):
    data=b'transaction_reference,amount,status,method,order_reference,refund_id\nGOOD-ROW,10,success,Bank transfer,,\nBAD-ROW,-1,success,Bank transfer,,\n'
    b=preview(data,'bad.csv','payments',1,actor()); db.session.flush()
    errors=validate_batch(b,{f:f for f in FIELDS['payments']}); db.session.flush()
    assert len(errors)==1
    assert ImportRowError.query.filter_by(row_id=b.rows[1].id).count()==1
    assert RefundPayment.query.filter_by(reference='GOOD-ROW').count()==0
    with pytest.raises(DomainError): confirm_batch(b)

def test_cross_store_allocation_rejected(app):
    p=record_payment(2,'OTHER-STORE',10,'success',1,actor()); db.session.flush()
    with pytest.raises(DomainError): allocate(p,first_refund(),1000,actor())

def test_xlsx_and_export_formula_safety(app,client):
    from openpyxl import Workbook,load_workbook
    book=Workbook(); ws=book.active; ws.append(['transaction_reference','amount','status','method','order_reference','refund_id']); ws.append(['XL-1',10,'success','Bank transfer','',''])
    buffer=io.BytesIO(); book.save(buffer)
    assert parse_file(buffer.getvalue(),'file.xlsx')[0]['amount']=='10'
    login(client); response=client.get('/reports?format=xlsx'); assert load_workbook(io.BytesIO(response.data)).active.max_row>=1

def test_resolve_reopen_without_duplicate(app,client):
    login(client); e=ReconciliationException.query.filter_by(status='open').first(); ident=e.id
    client.post(f'/exceptions/{ident}',data={'action':'resolve','reason':'Evidence reviewed and accepted'})
    assert e.status=='resolved'
    reconcile(actor()); db.session.flush(); assert e.status=='resolved'
    client.post(f'/exceptions/{ident}',data={'action':'reopen','reason':'New evidence'})
    assert e.status=='open'

def test_preference_cookie(app,client):
    login(client); response=client.post('/preferences',data={'page_size':'10'}); assert 'page_size=10' in response.headers['Set-Cookie']
    assert client.post('/preferences',data={'page_size':'9999'}).status_code==400
