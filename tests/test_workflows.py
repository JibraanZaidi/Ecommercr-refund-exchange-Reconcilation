import io
import pytest
from app.models import *
from app.services import *
from app.imports import *
from conftest import login

def aid(): return User.query.filter_by(email='admin@demo.local').one().id

def batch(kind,headers,row):
    import csv
    out=io.StringIO(); w=csv.writer(out); w.writerow(headers); w.writerow(row)
    b=preview(out.getvalue().encode(),kind+'.csv',kind,1,aid()); db.session.flush()
    assert validate_batch(b,{x:x for x in headers})==[]
    confirm_batch(b); db.session.commit(); return b

def test_orders_import_repeated(app):
    row=['TEST-ORDER','Test Buyer','test@example.test','Lahore','TEST-SKU','Face Oil','Skincare','2','800','COD-TEST']
    b=batch('orders',FIELDS['orders'],row); b2=batch('orders',FIELDS['orders'],row)
    assert b2.rows[0].status=='duplicate'
    order=SalesOrder.query.filter_by(reference='TEST-ORDER').one()
    assert len(order.items)==1 and order.items[0].quantity==2
    assert OrderPayment.query.filter_by(order_id=order.id).one().amount==160000

def test_receipt_import_repeated_and_mismatch(app):
    c=ReturnRequest.query.filter_by(reference='RET-DEMO-1-3').one()
    row=['RECEIPT-IMPORT',c.reference,c.items[0].order_item.variant.sku,2,'Lahore Returns Hub','damaged','rejected','quarantine']
    batch('receipts',FIELDS['receipts'],row); b=batch('receipts',FIELDS['receipts'],row)
    assert b.rows[0].status=='duplicate'
    assert ReconciliationException.query.filter_by(request_id=c.id,kind='receipt_mismatch',status='open').one()
    with pytest.raises(DomainError): close_case(c,aid())

def test_shipment_import_delivery_and_closure(app,client):
    c=ReturnRequest.query.filter_by(reference='RET-DEMO-1-5').one()
    rep=ReplacementOrder.query.filter_by(reference='EX-DEMO-1-5').one()
    batch('shipments',FIELDS['shipments'],[rep.reference,'Demo Courier','SHIP-IMPORT'])
    repeated=batch('shipments',FIELDS['shipments'],[rep.reference,'Demo Courier','SHIP-IMPORT'])
    assert repeated.rows[0].status=='duplicate'
    login(client,'warehouse')
    assert client.post(f'/replacements/{rep.id}/deliver',data={'reason':'Courier delivery receipt confirmed'}).status_code==302
    assert rep.status=='delivered'
    client.post('/logout'); login(client,'support')
    client.post(f'/cases/{c.id}/close',data={'reason':'All conditions verified'})
    assert c.status=='closed'

def test_draft_edit_delete(app,client):
    login(client,'support'); c=ReturnRequest.query.filter_by(reference='RET-DEMO-1-8').one(); ident=c.id
    assert client.get(f'/cases/{ident}/draft/edit').status_code==200
    item=c.order.items[0]
    client.post(f'/cases/{ident}/draft/edit',data={'reason_id':1,'resolution':'exchange','reason':'Customer changed resolution',f'qty_{item.id}':'2'})
    db.session.expire_all(); assert c.resolution=='exchange' and c.items[0].quantity==2
    client.post(f'/cases/{ident}/draft/delete'); assert db.session.get(ReturnRequest,ident) is None
    assert AuditEvent.query.filter_by(action='delete_draft',record_id=ident).one()

def test_http_import_full_flow(app,client):
    login(client,'accounts')
    data=b'transaction_reference,amount,status,method,order_reference,refund_id\nHTTP-IMPORT,500,success,Bank transfer,ORD-1001,1\n'
    response=client.post('/imports',data={'store_id':'1','kind':'payments','file':(io.BytesIO(data),'test.csv')},content_type='multipart/form-data')
    assert response.status_code==302
    location=response.headers['Location']; assert client.get(location).status_code==200
    response=client.post(location,data={'action':'map',**{x:x for x in FIELDS['payments']}},follow_redirects=True)
    assert response.status_code==200 and b'Confirm import' in response.data
    response=client.post(location,data={'action':'confirm'},follow_redirects=True)
    assert response.status_code==200 and RefundPayment.query.filter_by(reference='HTTP-IMPORT').count()==1

def test_pending_status_and_reversal_post(app,client):
    login(client,'accounts'); r=Refund.query.first()
    p=record_payment(1,'PENDING-HTTP',500,'pending',1,aid(),r.id); db.session.commit()
    client.post(f'/payments/{p.id}/status',data={'status':'success','reason':'Bank statement confirmed'})
    assert p.status=='success' and balances(r)['outstanding']==0
    client.post(f'/payments/{p.id}/reverse',data={'allocation_id':p.allocations[0].id,'amount':'100','reference':'HTTP-REV','reason':'Bank reversal'})
    assert balances(r)['outstanding']==10000

def test_manual_receipt_and_note_evidence(app,client):
    c=ReturnRequest.query.filter_by(reference='RET-DEMO-1-4').one()
    login(client,'warehouse')
    client.post(f'/cases/{c.id}/receive',data={'warehouse_id':1,'reference':'MANUAL-REC',f'qty_{c.items[0].id}':1,'condition':'sealed','inspection':'accepted','disposition':'restock'})
    assert WarehouseReceipt.query.filter_by(reference='MANUAL-REC').one()
    client.post('/logout'); login(client,'support')
    client.post(f'/cases/{c.id}/note',data={'reason':'Customer called'})
    client.post(f'/cases/{c.id}/evidence',data={'name':'Receipt scan','reason':'Document reference EVID-12'})
    assert CaseNote.query.filter_by(request_id=c.id).count()==1
    assert CaseAttachment.query.filter_by(request_id=c.id).count()==1

def test_user_crud_role_and_deactivation(app,client):
    login(client)
    client.post('/settings/users',data={'name':'New Operator','email':'new@demo.local','password':'SecurePass!123','role_id':3})
    u=User.query.filter_by(email='new@demo.local').one(); assert u.roles[0].name=='Warehouse'
    client.post(f'/settings/users/{u.id}',data={'action':'deactivate'}); assert not u.active
    client.post('/logout')
    assert b'incorrect' in client.post('/login',data={'email':u.email,'password':'SecurePass!123'}).data

def test_overdue_refund_setting(app):
    r=Refund.query.first(); r.created_at=now()-timedelta(days=10)
    reconcile(aid()); db.session.flush()
    assert ReconciliationException.query.filter_by(key=f'overdue_refund:{r.id}',status='open').one()

def test_split_receipts_and_approval_bounds(app):
    c=ReturnRequest.query.filter_by(reference='RET-DEMO-1-8').one()
    c.items[0].quantity=2; approve_case(c,aid(),'Two items'); db.session.flush()
    for ref in ['SPLIT-A','SPLIT-B']: receive(c,1,ref,[(c.items[0].id,1,'sealed','accepted','restock')],aid())
    assert sum(x.quantity for r in c.receipts for x in r.items)==2
    with pytest.raises(DomainError): approve_refund(c,6000,aid(),'Above returned amount')

def test_dashboard_open_link_matches(app,client):
    login(client); response=client.get('/cases?status=open&store=1')
    assert b'RET-DEMO-1-8' in response.data

def test_foreign_key_protects_used_master(app,client):
    login(client); original=ReturnReason.query.count()
    client.post('/settings/reasons/1',data={'action':'delete'})
    assert ReturnReason.query.count()==original

def test_formula_injection_escaped(app,client):
    from app.views import export_data
    with app.test_request_context():
        response=export_data(['Value'],[['=HYPERLINK("bad")']],'safe','csv')
        assert "'=HYPERLINK" in response.get_data(as_text=True)
