import sys, os

from flask import Flask, g, url_for
from peewee import Model
from playhouse.db_url import connect
from playhouse.postgres_ext import PostgresqlExtDatabase


# -- Reverse proxying (http://flask.pocoo.org/snippets/35/)
class RevProxy(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        return self.app(environ, start_response)


# -- App config
app = Flask('cropdb')
app.wsgi_app = RevProxy(app.wsgi_app)
app.config.from_envvar('CROPDB_SETTINGS')

db_url = os.environ.get('DATABASE_URL')

if db_url:
    db = connect(db_url)

else:
    db_args = [app.config.get('DB_NAME', 'cropdb')]
    db_kw = {
            'user': app.config['DB_USER'],
            'server_side_cursors': False,
            'register_hstore': False
            }

    db_host = app.config.get('DB_HOST')

    if db_host:
        db_kw['password'] = app.config['DB_PASS']
        db_kw['host'] = db_host

    db = PostgresqlExtDatabase(*db_args, **db_kw)


# -- Define BaseModel
class BaseModel(Model):
    class Meta:
        database = db

    @classmethod
    def key_name(cls):
        if hasattr(cls._meta, 'custom_key'):
            field_name = cls._meta.custom_key
        else:
            field_name = cls._meta.primary_key.name
        return field_name

    @classmethod
    def order_name(cls):
        if 'name' in cls._meta.fields:
            return 'name'
        else:
            return cls.key_name()

    @classmethod
    def keyfield(cls):
        return getattr(cls, cls.key_name())

    @classmethod
    def orderfield(cls):
        return getattr(cls, cls.order_name())

    @classmethod
    def modelname(cls):
        n = cls._meta.name
        return n

    @classmethod
    def modeltitle(cls):
        return cls.__name__

    def get_key(self):
        return getattr(self, self.key_name())

    def get_name(self):
        return getattr(self, self.order_name())


# -- Define DB models
from cropdb.auth.models import ApdUser, Session, Subscription
from cropdb.apd.models import (
        Chemical, ProdStatus, SalesStatus, Product, Sales, Method,
        Crop, PestType, Pest, CropPest, Application, Company, Brand
        )


# -- APD resource mapping
all_resources = [
    Chemical, ProdStatus, SalesStatus, Product, Sales, Method,
    Crop, PestType, Pest, CropPest, Application, Company, Brand
    ]
exposed = [Product, Chemical, Crop, Pest, Company, Brand]
link_resources = {m.modelname():m for m in exposed}
sub_resources = [m.modelname() for m in [Product, Crop, Company]]
resources = {m.modelname():m for m in all_resources}


# -- Namespace
def create_tables():
    tables = all_resources + [ApdUser, Session, Subscription]
    db.connect()
    db.create_tables(tables, safe=True)
    db.close()


def create_users():
    # admin
    admin_user, created = ApdUser.get_or_create(
            email=app.config['ADMIN_USER'], active=True, admin=True
            )

    if created:
        admin_user.set_pass(app.config['ADMIN_PASS'])
        admin_user.save()

    # normal user
    test_user, created = ApdUser.get_or_create(
            email=app.config['TEST_USER'], active=True
            )

    if created:
        test_user.set_pass(app.config['TEST_PASS'])
        test_user.save()

    # subscription
    Subscription.change(test_user, {'product':[2]})


def jinja_config():
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True
    app.jinja_env.globals.update(
            {m.modelname().capitalize():m for m in all_resources}
            )
    app.jinja_env.globals.update(
            sturl = lambda f: url_for('static', filename=f)
            )


# -- Init functions
create_tables()
create_users()
jinja_config()


# -- Init lifecycle
import cropdb.lifecycle


# -- Init endpoints
import cropdb.views.admin
import cropdb.views.user
import cropdb.views.apd
import cropdb.views.index
