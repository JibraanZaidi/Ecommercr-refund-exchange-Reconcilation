"""Server-rendered routes. Permissions are checked on every read/write endpoint."""
import csv, io
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, request, session, g, render_template, redirect, url_for, flash, abort, make_response, send_file
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from openpyxl import Workbook
from .models import *
from .services import *
from .imports import FIELDS, preview, validate_batch, confirm_batch, process

bp=Blueprint('web',__name__)
@bp.before_request
def load_user():
    g.user=db.session.get(User,session.get('user_id')) if session.get('user_id') else None
    if g.user and not g.user.active: session.clear(); g.user=None

def can(permission):
    return bool(g.user and any(r.name=='Admin' or any(p.name==permission for p in r.permissions) for r in g.user.roles))

def access(permission=None):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args,**kwargs):
            if not g.user: return redirect(url_for('web.login'))
            if permission and not can(permission): abort(403)
            return fn(*args,**kwargs)
        return wrapped
    return decorator

@bp.context_processor
def context(): return dict(can=can, stores=Store.query.order_by(Store.name).all(), balances=balances)

def commit(message):
    db.session.commit(); flash(message,'success')

def attempt(fn):
    try: fn(); commit('Changes saved.')
    except (DomainError, ValueError, TypeError, IntegrityError) as e:
        db.session.rollback(); flash('Referenced records, duplicate values or invalid fields prevent this change.' if isinstance(e,IntegrityError) else str(e),'error')

@bp.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        user=User.query.filter_by(email=request.form.get('email','').lower().strip()).first()
        if user and user.active and check_password_hash(user.password_hash,request.form.get('password','')):
            session.clear(); session['user_id']=user.id; session.permanent=True
            return redirect(url_for('web.dashboard'))
        flash('Email or password is incorrect.','error')
    return render_template('login.html')

@bp.post('/logout')
@access()
def logout(): session.clear(); return redirect(url_for('web.login'))

@bp.post('/preferences')
@access()
def preference():
    value=request.form.get('page_size','25')
    if value not in ('10','25','50'): abort(400)
    response=redirect(url_for('web.dashboard')); response.set_cookie('page_size',value,max_age=31536000,samesite='Lax',httponly=True,secure=request.is_secure)
    return response

def scoped(query,model):
    sid=request.args.get('store',type=int)
    if sid: query=query.filter(model.store_id==sid)
    for key,op in [('start','ge'),('end','lt')]:
        value=request.args.get(key)
        if value:
            try: date=datetime.strptime(value,'%Y-%m-%d')
            except ValueError: abort(400)
            query=query.filter(model.created_at>=date) if op=='ge' else query.filter(model.created_at<date+timedelta(days=1))
    return query

def cases_query():
    q=ReturnRequest.query.join(SalesOrder)
    if request.args.get('store',type=int): q=q.filter(SalesOrder.store_id==request.args.get('store',type=int))
    for key in ('start','end'):
        if request.args.get(key):
            try: d=datetime.strptime(request.args[key],'%Y-%m-%d')
            except ValueError: abort(400)
            q=q.filter(ReturnRequest.created_at>=d) if key=='start' else q.filter(ReturnRequest.created_at<d+timedelta(days=1))
    return q

def exception_query():
    q=scoped(ReconciliationException.query,ReconciliationException)
    if request.args.get('kind'): q=q.filter_by(kind=request.args['kind'])
    if request.args.get('status'): q=q.filter_by(status=request.args['status'])
    else: q=q.filter_by(status='open')
    return q

def table(title,headers,rows,subtitle='',actions=None):
    return render_template('table.html',title=title,headers=headers,rows=rows,subtitle=subtitle,actions=actions or [])

def page(query):
    size=int(request.cookies.get('page_size','25')) if request.cookies.get('page_size','25') in ('10','25','50') else 25
    return query.paginate(page=max(1,request.args.get('page',1,type=int)),per_page=size,error_out=False)

def choices(model,label='name',query=None):
    query = query if query is not None else model.query
    if hasattr(model,'archived'): query=query.filter(model.archived.is_(False))
    return [(x.id,str(getattr(x,label))) for x in query.all()]

def field(name,label=None,kind='text',options=None,value='',required=True):
    return dict(name=name,label=label or name.replace('_',' ').title(),kind=kind,options=options or [],value=value,required=required)

def form(title,fields,subtitle='',back='/'):
    for f in fields:
        if request.method=='POST': f['value']=request.form.get(f['name'],f['value'])
    return render_template('form.html',title=title,fields=fields,subtitle=subtitle,back=back)

@bp.get('/')
@access()
def dashboard():
    cases=cases_query().all(); case_ids=[c.id for c in cases]
    refunds=Refund.query.filter(Refund.request_id.in_(case_ids)).all()
    outstanding=sum(balances(r)['outstanding'] for r in refunds)
    exceptions=scoped(ReconciliationException.query,ReconciliationException).filter_by(status='open').all()
    totals={}
    for e in exceptions: totals[e.kind]=totals.get(e.kind,0)+1
    activity={}
    for r in refunds:
        month=r.created_at.strftime('%b %Y'); activity[month]=activity.get(month,0)+r.approved_amount
    return render_template('dashboard.html',title='Operations overview',cases=cases,refunds=refunds,
        outstanding=outstanding,exceptions=exceptions,types=totals,activity=activity,
        pending=sum(balances(r)['outstanding']>0 for r in refunds),open_cases=sum(c.status not in ('closed','cancelled') for c in cases))

@bp.get('/orders')
@access()
def orders():
    q=scoped(SalesOrder.query,SalesOrder)
    term=request.args.get('q','').strip()
    if term:
        q=q.join(Customer).filter(or_(SalesOrder.reference.ilike('%'+term+'%'),Customer.name.ilike('%'+term+'%'),
            SalesOrder.items.any(SalesOrderItem.variant.has(ProductVariant.sku.ilike('%'+term+'%'))),
            SalesOrder.id.in_(db.session.query(OrderPayment.order_id).filter(OrderPayment.reference.ilike('%'+term+'%')))))
    pagination=page(q.order_by(SalesOrder.id.desc()))
    return render_template('orders.html',title='Original orders',pagination=pagination)

@bp.get('/orders/<int:ident>')
@access()
def order_detail(ident):
    order=db.get_or_404(SalesOrder,ident)
    return render_template('order.html',title=order.reference,order=order,payments=OrderPayment.query.filter_by(order_id=ident).all())

@bp.route('/orders/new',methods=['GET','POST'])
@access('support')
def order_new():
    fields=[field('store_id','Store','select',choices(Store))]+[field(x,kind='number' if x=='quantity' else 'text') for x in FIELDS['orders']]
    if request.method=='POST':
        try:
            order,_=process('orders',request.form.to_dict(),positive(request.form['store_id']),g.user.id,None)
            audit(g.user.id,'manual_order',order); commit('Order line saved.'); return redirect(url_for('web.order_detail',ident=order.id))
        except (DomainError,ValueError,IntegrityError) as e: db.session.rollback(); flash(str(e) if not isinstance(e,IntegrityError) else 'Duplicate or invalid order.','error')
    return form('Enter an order line',fields,'Enter one row per SKU. Reuse the store and order reference to add another item.')

@bp.get('/cases')
@access()
def cases():
    q=cases_query()
    if request.args.get('status')=='open': q=q.filter(ReturnRequest.status.in_(['draft','approved']))
    elif request.args.get('status'): q=q.filter(ReturnRequest.status==request.args['status'])
    if request.args.get('q'): q=q.filter(ReturnRequest.reference.ilike('%'+request.args['q']+'%'))
    return render_template('cases.html',title='Return cases',pagination=page(q.order_by(ReturnRequest.id.desc())))

@bp.route('/orders/<int:ident>/return',methods=['GET','POST'])
@access('support')
def case_new(ident):
    order=db.get_or_404(SalesOrder,ident)
    fields=[field('reason_id','Reason','select',choices(ReturnReason)),field('resolution','Resolution','select',[('refund','Refund'),('exchange','Exchange')])]
    fields += [field('qty_'+str(i.id),f'{i.variant.sku} · purchased {i.quantity}','number',value='0',required=False) for i in order.items]
    if request.method=='POST':
        try:
            selected=[(i.id,request.form.get('qty_'+str(i.id))) for i in order.items if request.form.get('qty_'+str(i.id),'') not in ('','0')]
            case=create_case(order,selected,positive(request.form['reason_id']),request.form['resolution'],g.user.id)
            commit('Return draft created.'); return redirect(url_for('web.case_detail',ident=case.id))
        except (DomainError,IntegrityError) as e: db.session.rollback(); flash(str(e),'error')
    return form('Request a return',fields,'Enter quantities only for affected items; leave others at zero.')

@bp.get('/cases/<int:ident>')
@access()
def case_detail(ident):
    case=db.get_or_404(ReturnRequest,ident); exchange=ExchangeRequest.query.filter_by(request_id=ident).first()
    replacement=ReplacementOrder.query.filter_by(exchange_id=exchange.id).first() if exchange else None
    return render_template('case.html',title=case.reference,case=case,notes=CaseNote.query.filter_by(request_id=ident).all(),
        evidence=CaseAttachment.query.filter_by(request_id=ident).all(),replacement=replacement,
        exceptions=ReconciliationException.query.filter_by(request_id=ident,status='open').all(),
        exchange_lines=[(x, get(ProductVariant,x.variant_id)) for x in ExchangeItem.query.filter_by(exchange_id=exchange.id).all()] if exchange else [],
        approvals=RefundApproval.query.join(Refund).filter(Refund.request_id==ident).all(),
        inspections={x.receipt_item_id:(x,ItemDisposition.query.filter_by(inspection_id=x.id).first()) for x in ItemInspection.query.join(WarehouseReceiptItem).join(WarehouseReceipt).filter(WarehouseReceipt.request_id==ident).all()})

OPERATIONS={'approve':'support','cancel':'support','note':'support','evidence':'support','refund':'accounts','receive':'warehouse','replacement':'support','close':'support'}
@bp.route('/cases/<int:ident>/<operation>',methods=['GET','POST'])
@access()
def case_action(ident,operation):
    if operation not in OPERATIONS: abort(404)
    if not can(OPERATIONS[operation]): abort(403)
    c=db.get_or_404(ReturnRequest,ident)
    fields=[field('reason','Reason / note','textarea')]
    if operation=='refund': fields=[field('amount','Approved amount (PKR)',value=str(sum(i.quantity*i.order_item.unit_price for i in c.items)/100))]+fields
    if operation=='evidence': fields=[field('name','Evidence title'),field('reason','Evidence reference / description','textarea')]
    if operation=='receive':
        fields=[field('warehouse_id','Warehouse','select',choices(Warehouse)),field('reference','Receipt reference')]
        for i in c.items:
            fields += [field('qty_'+str(i.id),f'{i.order_item.variant.sku} received quantity','number',value='0',required=False)]
        fields += [field('condition',kind='select',options=[(x,x.title()) for x in ('sealed','opened','damaged')]),field('inspection',kind='select',options=[('accepted','Accepted'),('rejected','Rejected')]),field('disposition',kind='select',options=[(x,x.title()) for x in ('restock','quarantine','dispose')])]
    if operation=='replacement':
        ex=ExchangeRequest.query.filter_by(request_id=c.id).first()
        if not ex: abort(400)
        variants=choices(ProductVariant,'sku',ProductVariant.query.join(Product).filter(Product.store_id==c.order.store_id))
        fields=[field('variant_'+str(x.id),'Replacement SKU','select',variants,x.variant_id) for x in ExchangeItem.query.filter_by(exchange_id=ex.id)]
    if request.method=='POST':
        def update():
            reason=request.form.get('reason','').strip()
            if operation in ('approve','cancel','note','evidence','close') and not reason: raise DomainError('A reason or note is required.')
            if operation=='approve': approve_case(c,g.user.id,reason)
            elif operation=='refund': approve_refund(c,request.form['amount'],g.user.id,reason)
            elif operation=='cancel':
                if c.status!='draft': raise DomainError('Only unapproved drafts can be cancelled.')
                transition(c,'cancelled',g.user.id,reason)
            elif operation=='note': db.session.add(CaseNote(request_id=c.id,actor_id=g.user.id,body=reason)); audit(g.user.id,'note',c,reason)
            elif operation=='evidence':
                if not request.form.get('name','').strip(): raise DomainError('Evidence title required.')
                db.session.add(CaseAttachment(request_id=c.id,actor_id=g.user.id,name=request.form['name'],evidence=reason)); audit(g.user.id,'evidence',c,reason)
            elif operation=='receive':
                lines=[(i.id,request.form.get('qty_'+str(i.id)),request.form['condition'],request.form['inspection'],request.form['disposition']) for i in c.items if request.form.get('qty_'+str(i.id),'') not in ('','0')]
                receive(c,positive(request.form['warehouse_id']),request.form['reference'],lines,g.user.id)
            elif operation=='replacement': create_replacement(c,{k.replace('variant_',''):v for k,v in request.form.items() if k.startswith('variant_')},g.user.id)
            elif operation=='close': close_case(c,g.user.id)
            reconcile(g.user.id,c.order.store_id)
        attempt(update); return redirect(url_for('web.case_detail',ident=ident))
    return form(operation.title()+' · '+c.reference,fields,back=url_for('web.case_detail',ident=ident))

@bp.get('/refunds')
@access()
def refunds():
    ids=[c.id for c in cases_query().all()]
    data=Refund.query.filter(Refund.request_id.in_(ids)).all()
    if request.args.get('outstanding'): data=[r for r in data if balances(r)['outstanding']]
    rows=[([str(r.id),r.case.reference,balances(r)['approved']/100,balances(r)['paid']/100,balances(r)['outstanding']/100,balances(r)['overpaid']/100],url_for('web.case_detail',ident=r.request_id)) for r in data]
    return table('Refund ledger',['ID','Case','Approved PKR','Net paid PKR','Outstanding PKR','Overpaid PKR'],rows)

@bp.get('/payments')
@access('accounts')
def payments():
    p=page(scoped(RefundPayment.query,RefundPayment).order_by(RefundPayment.id.desc()))
    return render_template('payments.html',title='Payment records',pagination=p)

@bp.route('/payments/new',methods=['GET','POST'])
@access('accounts')
def payment_new():
    fields=[field('store_id','Store','select',choices(Store)),field('reference','Transaction reference'),field('amount','Amount (PKR)'),field('status',kind='select',options=[(s,s.title()) for s in ('success','pending','failed')]),field('method_id','Method','select',choices(RefundPaymentMethod)),field('refund_id','Explicit refund allocation','select',[('','Leave unmatched')]+choices(Refund,'id'),required=False),field('order_reference',required=False)]
    if request.method=='POST':
        def save():
            record_payment(positive(request.form['store_id']),request.form['reference'],request.form['amount'],request.form['status'],positive(request.form['method_id']),g.user.id,request.form.get('refund_id') or None,request.form.get('order_reference','')); reconcile(g.user.id)
        attempt(save); return redirect(url_for('web.payments'))
    return form('Record refund payment',fields,'No funds are transferred. This records payment evidence only.')

@bp.route('/payments/<int:ident>/<operation>',methods=['GET','POST'])
@access('accounts')
def payment_action(ident,operation):
    p=db.get_or_404(RefundPayment,ident)
    if operation=='allocate': fields=[field('refund_id','Approved refund','select',choices(Refund,'id')),field('amount','Amount to allocate (PKR)')]
    elif operation=='status': fields=[field('status',kind='select',options=[('success','Successful'),('failed','Failed')]),field('reason','Reason','textarea')]
    elif operation=='reverse': fields=[field('allocation_id','Allocation','select',[(a.id,f'Refund {a.refund_id}: {a.amount/100} PKR') for a in p.allocations]),field('amount','Reversal amount (PKR)'),field('reference','Reversal reference'),field('reason','Reason','textarea')]
    else: abort(404)
    if request.method=='POST':
        def change():
            if operation=='allocate': allocate(p,get(Refund,request.form['refund_id']),money(request.form['amount']),g.user.id)
            elif operation=='status':
                if p.status!='pending' or request.form['status'] not in ('success','failed') or not request.form.get('reason','').strip(): raise DomainError('Only pending payments can transition, with a reason.')
                p.status=request.form['status']; audit(g.user.id,'payment_status',p,request.form['reason'])
            else:
                a=get(RefundPaymentAllocation,request.form['allocation_id'])
                if a.payment_id!=p.id: raise DomainError('Allocation belongs to another payment.')
                reverse(a,request.form['amount'],request.form['reference'],g.user.id,request.form['reason'])
            db.session.flush(); reconcile(g.user.id)
        attempt(change); return redirect(url_for('web.payments'))
    return form(operation.title()+' · '+p.reference,fields)

@bp.route('/replacements/<int:ident>/<operation>',methods=['GET','POST'])
@access()
def replacement_action(ident,operation):
    permission='accounts' if operation=='difference' else 'warehouse'
    if not can(permission): abort(403)
    rep=db.get_or_404(ReplacementOrder,ident)
    fields=[field('reason','Evidence / note','textarea')]
    if operation=='dispatch': fields=[field('carrier_id','Carrier','select',choices(Carrier)),field('tracking','Tracking number')]
    elif operation not in ('deliver','difference'): abort(404)
    if request.method=='POST':
        def save():
            if operation=='dispatch': dispatch(rep,positive(request.form['carrier_id']),request.form['tracking'],g.user.id)
            else:
                if not request.form.get('reason','').strip(): raise DomainError('Evidence note required.')
                if operation=='difference': rep.difference_settled=True
                else:
                    if rep.status!='dispatched' or not rep.shipments: raise DomainError('Dispatch before delivery.')
                    rep.status='delivered'; rep.shipments[0].status='delivered'
                    db.session.add(ReplacementShipmentEvent(shipment_id=rep.shipments[0].id,status='delivered',note=request.form['reason']))
                audit(g.user.id,operation,rep,request.form['reason'])
            reconcile(g.user.id)
        attempt(save); return redirect(url_for('web.case_detail',ident=get(ExchangeRequest,rep.exchange_id).request_id))
    return form(operation.title()+' · '+rep.reference,fields)

@bp.get('/exceptions')
@access()
def exceptions():
    return render_template('exceptions.html',title='Reconciliation exceptions',pagination=page(exception_query().order_by(ReconciliationException.id.desc())))

@bp.post('/reconcile')
@access('accounts')
def run_reconcile():
    attempt(lambda: reconcile(g.user.id,request.form.get('store_id',type=int)))
    return redirect(url_for('web.exceptions'))

@bp.route('/exceptions/<int:ident>',methods=['GET','POST'])
@access('accounts')
def exception_detail(ident):
    e=db.get_or_404(ReconciliationException,ident)
    if request.method=='POST':
        def save():
            action=request.form.get('action'); reason=request.form.get('reason','').strip()
            if action not in ('resolve','reopen','note','assign') or not reason: raise DomainError('Action and explanation/evidence required.')
            if action=='resolve': e.status='resolved'; e.resolution_fingerprint=e.fingerprint
            elif action=='reopen': e.status='open'
            elif action=='assign': e.assigned_to=get(User,request.form['assigned_to']).id
            db.session.add(ExceptionResolution(exception_id=e.id,actor_id=g.user.id,action=action,reason=reason)); audit(g.user.id,action,e,reason)
        attempt(save); return redirect(url_for('web.exception_detail',ident=ident))
    return render_template('exception.html',title=e.kind.replace('_',' ').title(),e=e,users=User.query.filter_by(active=True).all(),history=ExceptionResolution.query.filter_by(exception_id=e.id).all())

@bp.route('/imports',methods=['GET','POST'])
@access()
def imports():
    allowed=[k for k,p in [('orders','support'),('payments','accounts'),('receipts','warehouse'),('shipments','warehouse')] if can(p)]
    if request.method=='POST':
        if request.form.get('kind') not in allowed: abort(403)
        try:
            upload=request.files.get('file')
            if not upload or not upload.filename: raise DomainError('Select a CSV or XLSX file.')
            batch=preview(upload.read(),upload.filename,request.form['kind'],positive(request.form['store_id']),g.user.id)
            commit('File uploaded. Review the column mapping.'); return redirect(url_for('web.import_detail',ident=batch.id))
        except (DomainError,ValueError) as e: db.session.rollback(); flash(str(e),'error')
    batches=ImportBatch.query if can('admin') else ImportBatch.query.filter_by(actor_id=g.user.id)
    return render_template('imports.html',title='Import center',allowed=allowed,batches=batches.order_by(ImportBatch.id.desc()).limit(50).all())

@bp.route('/imports/<int:ident>',methods=['GET','POST'])
@access()
def import_detail(ident):
    batch=db.get_or_404(ImportBatch,ident)
    permission={'orders':'support','payments':'accounts','receipts':'warehouse','shipments':'warehouse'}[batch.kind]
    if not can(permission) or (batch.actor_id!=g.user.id and not can('admin')): abort(403)
    if request.method=='POST':
        def save():
            if request.form.get('action')=='confirm': confirm_batch(batch)
            elif request.form.get('action')=='map':
                mappings={k:request.form.get(k,'') for k in FIELDS[batch.kind]}
                errors=validate_batch(batch,mappings)
                if errors: flash(f'{len(errors)} row(s) need correction. Upload a corrected file if values are invalid.','error')
            else: raise DomainError('Invalid import action.')
        attempt(save); return redirect(url_for('web.import_detail',ident=ident))
    mappings={m.target_column:m.source_column for m in ImportColumnMapping.query.filter_by(batch_id=ident)}
    errors=ImportRowError.query.join(ImportRow).filter(ImportRow.batch_id==ident).all()
    return render_template('import_detail.html',title=f'Import #{ident}',batch=batch,fields=FIELDS[batch.kind],headers=list(batch.rows[0].payload),mappings=mappings,errors=[(get(ImportRow,e.row_id).row_number,e.message) for e in errors])

@bp.get('/samples/<kind>.<extension>')
@access()
def sample(kind,extension):
    if kind not in FIELDS or extension not in ('csv','xlsx'): abort(404)
    return export_data(FIELDS[kind],[],kind+'-template',extension)

def export_data(headers,rows,name,extension):
    # Neutralize formula injection in both spreadsheet formats.
    def safe(x): return "'"+x if isinstance(x,str) and x.startswith(('=','+','-','@','\t','\r')) else x
    if extension=='xlsx':
        book=Workbook(); sheet=book.active; sheet.append(headers)
        for row in rows: sheet.append([safe(x) for x in row])
        sheet.freeze_panes='A2'; sheet.auto_filter.ref=sheet.dimensions
        output=io.BytesIO(); book.save(output); output.seek(0)
        return send_file(output,as_attachment=True,download_name=name+'.xlsx',mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    out=io.StringIO(); writer=csv.writer(out); writer.writerow(headers); writer.writerows([[safe(x) for x in row] for row in rows])
    response=make_response(out.getvalue()); response.headers['Content-Type']='text/csv; charset=utf-8'; response.headers['Content-Disposition']=f'attachment; filename="{name}.csv"'; return response

@bp.get('/reports')
@access('accounts')
def reports():
    kind=request.args.get('report','outstanding'); ids=[c.id for c in cases_query().all()]
    if kind=='outstanding':
        headers=['Order','Case','Status','Approved PKR','Paid PKR','Outstanding PKR','Overpaid PKR','Reason']
        rows=[[r.case.order.reference,r.case.reference,r.status,balances(r)['approved']/100,balances(r)['paid']/100,balances(r)['outstanding']/100,balances(r)['overpaid']/100,'Net successful allocations'] for r in Refund.query.filter(Refund.request_id.in_(ids)).all() if balances(r)['outstanding']]
    elif kind=='reasons':
        headers=['Order','Case','Status','Product','Reason','Quantity']
        rows=[[c.order.reference,c.reference,c.status,i.order_item.variant.name,c.reason.name,i.quantity] for c in ReturnRequest.query.filter(ReturnRequest.id.in_(ids)).all() for i in c.items]
    else:
        headers=['Order','Case','Status','Exception','Expected','Recorded','Reason']
        q=exception_query()
        groups={'payments':['short_refund','pending_refund','overdue_refund','overpayment','potential_duplicate'],'unmatched':['unmatched_payment'],'exchanges':['missing_replacement','overdue_replacement'],'warehouse':['missing_receipt','receipt_mismatch']}
        if kind in groups: q=q.filter(ReconciliationException.kind.in_(groups[kind]))
        elif kind!='exceptions': abort(400)
        rows=[]
        for e in q.all():
            c=db.session.get(ReturnRequest,e.request_id) if e.request_id else None
            factor=1 if e.kind in ('missing_receipt','receipt_mismatch') else 100
            rows.append([c.order.reference if c else '',c.reference if c else '',e.status,e.kind,e.expected/factor,e.recorded/factor,e.detail])
    extension=request.args.get('format')
    if extension in ('csv','xlsx'): return export_data(headers,rows,'reconciliation-'+kind,extension)
    return render_template('reports.html',title='Reports & exports',headers=headers,rows=rows,report=kind)

# Explicit allowlist: operational records cannot be edited through this generic CRUD.
MASTERS={
 'stores':(Store,['name','platform']), 'customers':(Customer,['store_id','name','email','city']),
 'products':(Product,['store_id','name','category']), 'variants':(ProductVariant,['product_id','sku','name','price']),
 'reasons':(ReturnReason,['name']), 'warehouses':(Warehouse,['name','city']),
 'carriers':(Carrier,['name']), 'methods':(RefundPaymentMethod,['name']),
 'settings':(StoreSetting,['store_id','refund_days','replacement_days']),
 'users':(User,['name','email']),
}
REFERENCES={'store_id':Store,'product_id':Product}
@bp.route('/settings/<kind>',methods=['GET','POST'])
@bp.route('/settings/<kind>/<int:ident>',methods=['GET','POST'])
@access('admin')
def master(kind,ident=None):
    if kind not in MASTERS: abort(404)
    model,names=MASTERS[kind]; obj=db.get_or_404(model,ident) if ident else None
    if request.method=='POST':
        def save():
            nonlocal obj
            action=request.form.get('action','save')
            if action=='delete':
                if not obj or kind in ('users','settings'): raise DomainError('This record cannot be deleted; deactivate users instead.')
                audit(g.user.id,'delete',obj); db.session.delete(obj); return
            if action=='archive':
                if not obj or not hasattr(obj,'archived'): raise DomainError('Archival unavailable.')
                obj.archived=not obj.archived; audit(g.user.id,'toggle_archive',obj); return
            if action=='deactivate':
                if kind!='users' or not obj or obj.id==g.user.id: raise DomainError('Cannot deactivate yourself.')
                obj.active=not obj.active; audit(g.user.id,'toggle_active',obj); return
            if action!='save': raise DomainError('Invalid action.')
            data={}
            for name in names:
                value=request.form.get(name,'').strip()
                if not value: raise DomainError(name.replace('_',' ')+' is required.')
                if name in REFERENCES: value=get(REFERENCES[name],value).id
                elif name=='price': value=money(value)
                elif name.endswith('_days'): value=positive(value)
                elif len(value)>180: raise DomainError(name+' is too long.')
                data[name]=value
            if kind=='stores' and data['platform'] not in ('Shopify','WooCommerce'): raise DomainError('Use Shopify or WooCommerce.')
            if kind=='users':
                data['email']=data['email'].lower()
                password=request.form.get('password','')
                if not obj and len(password)<10: raise DomainError('New users need a password of at least 10 characters.')
                if password:
                    if len(password)<10: raise DomainError('Password must contain at least 10 characters.')
                    data['password_hash']=generate_password_hash(password)
            if obj:
                # Relationships of used master records are immutable.
                for name in REFERENCES:
                    if name in data and getattr(obj,name)!=data[name]: raise DomainError('Parent/store cannot be reassigned; create a new master record.')
                for name,value in data.items(): setattr(obj,name,value)
            else: obj=model(**data); db.session.add(obj); db.session.flush()
            if kind=='users':
                role=get(Role,request.form.get('role_id'))
                if obj.id==g.user.id and role.name!='Admin': raise DomainError('Cannot remove your own admin role.')
                UserRole.query.filter_by(user_id=obj.id).delete(); db.session.add(UserRole(user_id=obj.id,role_id=role.id))
            audit(g.user.id,'save_master',obj)
        attempt(save); return redirect(url_for('web.master',kind=kind))
    fields=[]
    for name in names:
        value=getattr(obj,name,'') if obj else ''
        if name=='price' and obj: value=obj.price/100
        fields.append(field(name,kind='select' if name in REFERENCES else 'text',options=choices(REFERENCES[name]) if name in REFERENCES else [],value=value))
    if kind=='users': fields += [field('password','New password (blank keeps existing)','password',required=not obj),field('role_id','Role','select',choices(Role),obj.roles[0].id if obj and obj.roles else '')]
    return render_template('master.html',title=kind.title(),fields=fields,records=page(model.query.order_by(model.id.desc())),names=names,kind=kind,obj=obj,masters=MASTERS)

@bp.get('/audit')
@access('admin')
def audits():
    p=page(AuditEvent.query.order_by(AuditEvent.id.desc()))
    return render_template('audit.html',title='Audit trail',pagination=p)

@bp.route('/cases/<int:ident>/draft/edit',methods=['GET','POST'])
@access('support')
def edit_draft(ident):
    c=db.get_or_404(ReturnRequest,ident)
    if c.status!='draft': abort(400,description='Only draft requests can be edited.')
    fields=[field('reason_id','Reason','select',choices(ReturnReason),c.reason_id),field('resolution','Resolution','select',[('refund','Refund'),('exchange','Exchange')],c.resolution)]
    quantities={x.order_item_id:x.quantity for x in c.items}
    fields += [field('qty_'+str(x.id),x.variant.sku+' quantity','number',value=quantities.get(x.id,0),required=False) for x in c.order.items]
    fields.append(field('reason','Change reason','textarea'))
    if request.method=='POST':
        def save():
            if not request.form.get('reason','').strip(): raise DomainError('Change reason required.')
            if request.form.get('resolution') not in ('refund','exchange'): raise DomainError('Invalid resolution.')
            c.reason_id=get(ReturnReason,request.form['reason_id']).id; c.resolution=request.form['resolution']
            selected=[]
            for item in c.order.items:
                value=request.form.get('qty_'+str(item.id),'0') or '0'
                if value=='0': continue
                quantity=positive(value)
                if quantity>item.quantity: raise DomainError('Requested quantity exceeds purchased quantity.')
                selected.append((item,quantity))
            if not selected: raise DomainError('Select at least one item.')
            for line in list(c.items): db.session.delete(line)
            db.session.flush()
            for item,quantity in selected: db.session.add(ReturnRequestItem(request_id=c.id,order_item_id=item.id,quantity=quantity))
            transition(c,'draft',g.user.id,request.form['reason'])
        attempt(save); return redirect(url_for('web.case_detail',ident=ident))
    return form('Edit draft · '+c.reference,fields)

@bp.post('/cases/<int:ident>/draft/delete')
@access('support')
def delete_draft(ident):
    c=db.get_or_404(ReturnRequest,ident)
    def remove():
        if c.status!='draft': raise DomainError('Only draft requests can be deleted.')
        audit(g.user.id,'delete_draft',c,'Unapproved draft removed')
        for model in (CaseNote,CaseAttachment,ReturnStatusEvent,ReturnRequestItem):
            for child in model.query.filter_by(request_id=c.id).all(): db.session.delete(child)
        db.session.flush()
        db.session.expire(c, ['items','events'])
        db.session.delete(c)
    attempt(remove); return redirect(url_for('web.cases'))
