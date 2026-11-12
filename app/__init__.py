import os
from pathlib import Path
from datetime import timedelta
from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import event
from sqlalchemy.engine import Engine
from .models import db

@event.listens_for(Engine, 'connect')
def sqlite_foreign_keys(connection, _):
    if connection.__class__.__module__.startswith('sqlite3'):
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA busy_timeout=5000')

def create_app(config=None):
    app = Flask(__name__)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    secret = os.environ.get('SECRET_KEY')
    if not secret and not (config and config.get('TESTING')):
        raise RuntimeError('Set SECRET_KEY in .env before starting the application.')
    app.config.update(SECRET_KEY=secret or 'test-only', SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL','sqlite:///reconcile.sqlite'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False, MAX_CONTENT_LENGTH=8*1024*1024,
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.environ.get('APP_ENV')=='production', PERMANENT_SESSION_LIFETIME=timedelta(hours=8))
    if config: app.config.update(config)
    db.init_app(app); CSRFProtect(app)
    from .views import bp
    app.register_blueprint(bp)
    from .seed import register_cli
    register_cli(app)
    app.jinja_env.filters['money'] = lambda x: f'Rs. {int(x or 0)/100:,.2f}'
    for code in (400,403,404,413,500):
        app.register_error_handler(code, lambda e: (render_template('error.html', error=e), e.code))
    return app
