'''
    tests
    —————

    Testing base class.

    :copyright: (c) 2015 by Anshul Sirur.
'''
import unittest as ut
import os
import tempfile as tmp

from flask import json
from peewee import SqliteDatabase

# Locals
from cropdb import app, db
from cropdb.auth.models import User


def get_string(rv):
    return rv.data.decode('utf8')

def get_json(rv):
    return json.loads(get_string(rv))


class Proxy(object):
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        environ['REMOTE_ADDR'] = environ.get('REMOTE_ADDR', '127.0.0.1')
        return self.app(environ, start_response)


class TestBase(ut.TestCase):
    def setUp(self):
        self.admin, c = User.register_user('admin@example.com')
        self.admin._pwd = 'winterbottom'
        self.admin.set_pass(self.admin._pwd)
        self.admin.admin = True
        self.admin.active = True
        self.admin.save()

        self.normal, c = User.register_user('norm@example.com')
        self.normal._pwd = 'lugnuts'
        self.normal.set_pass(self.normal._pwd)
        self.normal.active = True
        self.normal.save()

        self.inactive, c = User.register_user('inact@example.com')
        self.inactive._pwd = 'pants'
        self.inactive.set_pass(self.inactive._pwd)
        self.inactive.save()

        self.banned, c = User.register_user('ban@example.com')
        self.banned._pwd = 'badman'
        self.banned.set_pass(self.banned._pwd)
        self.banned.active = True
        self.banned.banned = True
        self.banned.save()

        app.debug = False
        app.wsgi_app = Proxy(app.wsgi_app)
        self.cli = app.test_client(use_cookies=True)

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)
