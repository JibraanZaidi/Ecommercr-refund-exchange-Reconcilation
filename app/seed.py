"""Repeatable demo initialization. Seed refuses to overwrite an existing workspace."""
import click
from sqlalchemy import inspect
from werkzeug.security import generate_password_hash
from .models import *
from .services import *

def seed():
    if User.query.first(): return False
    roles={}
    for name in ['Admin','Customer Support','Warehouse','Accounts']:
        r=Role(name=name); db.session.add(r); db.session.flush(); roles[name]=r
    for name,role_name in [('admin','Admin'),('support','Customer Support'),('warehouse','Warehouse'),('accounts','Accounts')]:
        p=Permission(name=name); db.session.add(p); db.session.flush(); db.session.add(RolePermission(role_id=roles[role_name].id,permission_id=p.id))
    users={}
    for email,name,role in [('admin','Jibraan Ali Zaidi Manager','Admin'),('support','Maira Support','Customer Support'),('warehouse','Rayan Warehouse','Warehouse'),('accounts','Dania Accounts','Accounts')]:
        u=User(email=email+'@demo.local',name=name,password_hash=generate_password_hash('DemoPass!2026')); db.session.add(u); db.session.flush()
        db.session.add(UserRole(user_id=u.id,role_id=roles[role].id)); users[email]=u
    reasons=[]
    for name in ['Damaged package','Wrong item received','Changed mind','Quality concern']:
        r=ReturnReason(name=name); db.session.add(r); reasons.append(r)
    wh=Warehouse(name='Lahore Returns Hub',city='Lahore'); db.session.add(wh)
    method=RefundPaymentMethod(name='Bank transfer'); db.session.add(method)
    db.session.add(RefundPaymentMethod(name='Wallet')); db.session.add(Carrier(name='Demo Courier')); db.session.flush()
    products=[('Rose Cleanser','Skincare',250000),('Herbal Shampoo','Haircare',120000),('Mango Pickle','Food',85000),('Mint Herbal Tea','Herbal',65000)]
    for sidx,name in enumerate(['Sage Basket','Meadow Essentials']):
        store=Store(name=name,platform='Shopify' if sidx==0 else 'WooCommerce'); db.session.add(store); db.session.flush()
        db.session.add(StoreSetting(store_id=store.id,refund_days=7,replacement_days=3))
        variants=[]
        for idx,(pname,category,price) in enumerate(products):
            p=Product(store_id=store.id,name=pname,category=category); db.session.add(p); db.session.flush()
            v=ProductVariant(product_id=p.id,sku=f'S{store.id}-{idx+1:03}',name=pname+' · Standard',price=price); db.session.add(v); variants.append(v)
        db.session.flush()
        for n in range(1,9):
            customer=Customer(store_id=store.id,name=['Amina Faraz','Hamza Kaleem','Zoya Asif','Bilal Nadeem'][n%4],email=f'customer{n}@store{store.id}.example',city=['Lahore','Karachi','Islamabad','Multan'][n%4])
            db.session.add(customer); db.session.flush()
            order=SalesOrder(store_id=store.id,customer_id=customer.id,reference=f'ORD-{1000+n}')
            db.session.add(order); db.session.flush()
            variant=variants[0] if n==1 else variants[n%4]
            item=SalesOrderItem(order_id=order.id,variant_id=variant.id,quantity=2,unit_price=variant.price); db.session.add(item); db.session.flush()
            db.session.add(OrderPayment(order_id=order.id,reference=f'COD-{store.id}-{n}',amount=item.quantity*item.unit_price,method='COD'))
            case=create_case(order,[(item.id,1)],reasons[n%4].id,'exchange' if n in (4,5) else 'refund',users['support'].id)
            case.reference=f'RET-DEMO-{store.id}-{n}'
            if n==8: continue
            approve_case(case,users['support'].id,'Demo request approved after customer review')
            if n not in (3,4): receive(case,wh.id,f'WH-{store.id}-{n}',[(case.items[0].id,1,'sealed','accepted','restock')],users['warehouse'].id)
            if n in (4,5):
                if n==5:
                    rep=create_replacement(case,{},users['support'].id); rep.reference=f'EX-DEMO-{store.id}-{n}'; rep.deadline=now()-timedelta(days=2)
                continue
            refund=approve_refund(case,str(variant.price/100),users['accounts'].id,'Return merchandise approved at original price')
            if n==1: record_payment(store.id,f'DEMO-PART-{store.id}',2000,'success',method.id,users['accounts'].id,refund.id,order.reference)
            elif n==2:
                record_payment(store.id,f'DEMO-FULL-{store.id}',str(variant.price/100),'success',method.id,users['accounts'].id,refund.id,order.reference)
                record_payment(store.id,f'DEMO-EXCESS-{store.id}',200,'success',method.id,users['accounts'].id,refund.id,order.reference)
            elif n==6: record_payment(store.id,f'DEMO-FAILED-{store.id}',str(variant.price/100),'failed',method.id,users['accounts'].id,refund.id,order.reference)
            elif n==7:
                payment=record_payment(store.id,f'DEMO-REVERSED-{store.id}',str(variant.price/100),'success',method.id,users['accounts'].id,refund.id,order.reference)
                reverse(payment.allocations[0],100,f'DEMO-REV-{store.id}',users['accounts'].id,'Demo bank reversal')
        record_payment(store.id,f'DEMO-UNMATCHED-{store.id}',300,'success',method.id,users['accounts'].id,order_reference='ORD-UNKNOWN')
    db.session.flush(); reconcile(users['accounts'].id); db.session.commit(); return True

def register_cli(app):
    @app.cli.command('init-db')
    def init_db():
        db.create_all(); click.echo('Database initialized; existing data preserved.')
    @app.cli.command('seed')
    def seed_command():
        click.echo('Fictional demo data created.' if seed() else 'Existing users found; seed skipped to preserve data.')
    @app.cli.command('verify-schema')
    def verify_schema():
        models=len(db.Model.registry.mappers); tables=len(inspect(db.engine).get_table_names())
        click.echo(f'Mapped models: {models}; physical tables: {tables}')
        if models<40 or tables<40: raise click.ClickException('Minimum model/table count not met.')
    @app.cli.command('reconcile')
    def reconciliation_command():
        run=reconcile(); db.session.commit(); click.echo(f'Run {run.id}: {run.exception_count} findings')
