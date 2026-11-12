import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from app import create_app
from app.models import db,User
from app.seed import seed

@pytest.fixture()
def app(tmp_path):
    application=create_app({'TESTING':True,'SQLALCHEMY_DATABASE_URI':'sqlite:///'+str(tmp_path/'test.sqlite'),'WTF_CSRF_ENABLED':False})
    with application.app_context():
        db.create_all(); seed(); yield application; db.session.remove(); db.drop_all()

@pytest.fixture()
def client(app): return app.test_client()

def login(client,role='admin'):
    return client.post('/login',data={'email':role+'@demo.local','password':'DemoPass!2026'},follow_redirects=True)
