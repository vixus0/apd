'''
    sleep
    —————

    A simple SQL REST framework based on peewee and flask.

    :copyright: (c) 2015 by Anshul Sirur.
    :license: BSD
'''
from peewee import BaseModel, Model, Database, ForeignKeyField
from jinja2 import Environment, FileSystemLoader
import re, json, pdfkit


class Sleep(object):
    name = 'sleep'
    db = None
    models = {}

    @staticmethod
    def _table_func(cls):
        return re.sub('[^\w]+', '_', cls.__name__.lower())

    @classmethod
    def _add_model(cls, model):
        '''Adds a model to Sleep.'''
        name = model._meta.model_name
        cls.models[name] = model
        if cls.db:
            cls.db.connect()
            model.create_table()
            cls.db.close()

    @classmethod
    def init_db(cls, db):
        cls.db = db
        for v in cls.models.values():
            v._meta.database = cls.db
        cls.db.create_tables(cls.models.values())

    @classmethod
    def pre_request(cls):
        '''Should be called before any calls to request().'''
        if cls.db:
            cls.db.connect()

    @classmethod
    def end_request(cls):
        '''Should be called after any calls to request().'''
        if cls.db:
            cls.db.close()

    @classmethod
    def request(cls, request):
        '''Carries out an HTTP request on the API.'''
        if request.model not in cls.models:
            response = Response.not_found(request)
        else:
            model = cls.models[request.model]

            try:
                method = getattr(cls, '_'+request.method)
            except AttributeError:
                response = Response.error(request, 'Unknown method.')
            except Exception:
                response = Response.error(request, 'Server error.')

            response = method(model, request)

        return response

    @classmethod
    def _GET(cls, model, request):
        if request.key:
            try:
                item = model.get(model.key() == request.key)
                resp = Response.ok(request, data=item)
            except model.DoesNotExist:
                resp = Response.not_found(request)
        else:
            idx = getattr(request, 'idx', None)

            if idx:
                items = model.select().where(model.key() << idx).order_by(model.orderfield())
            else:
                items = model.select().order_by(model.orderfield())

            resp = Response.ok(request, data=items)

        return resp

    @classmethod
    def _POST(cls, model, request):
        data = request.data
        try:
            item = model.create(**data) 
        except IntegrityError:
            return Response.conflict(request)
        return Response.created(request, data=item)

    @classmethod
    def _PUT(cls, model, request):
        data = request.data

        if request.key:
            upd = model.update(**data).where(model.key() == request.key)
            upd.execute()
            item = model.get(model.key() == request.key)
            resp = Response.ok(request, data=item)
        else:
            resp = Response.not_found(request)

        return resp

    @classmethod
    def _DELETE(cls, model, request):
        resp = cls._GET(model, request)
        if resp:
            item = resp.data
            item.delete_instance()
            resp = Response.ok(request)
        return resp


class Request(object):
    def __init__(self, method, model, key=None, args=None, data=None, idx=None):
        '''
        Create a Request object.

        Arguments:
        method -- The HTTP method (eg. 'GET', 'POST', 'PUT') for this request.
        model -- The requested model type.
        key -- A model item ID, required for GET requests.
        args -- A dict-like object containing additional query string parameters.
        data -- A dict-like object containing POST/PUT data.
        accepts -- The dict of accepted mimetypes in Werkzeug format.
        '''
        self.method = method
        self.model = model
        self.key = key
        self.args = args if args else {}
        self.data = data
        self.idx = idx

    def __hash__(self):
        return hash((method, model, key, args, idx))

    def __eq__(self, other):
        s = (self.method, self.model, self.key, self.idx) == \
                (other.method, other.model, other.key, other.idx)

        d = self.args.keys() == other.args.keys() and \
                self.args.values() == other.args.values()

        return s and d

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return '<Request: {}, {}, {}>'.format(method, model, key)

    @classmethod
    def get(cls, model, key=None, args=None):
        return cls('GET', model, key, args)

    @classmethod
    def post(cls, model, data):
        return cls('POST', model, None, None, data)

    @classmethod
    def put(cls, model, key, data):
        return cls('PUT', model, key, None, data)

    @classmethod
    def delete(cls, model, key):
        return cls('DELETE', model, key)


class Response(object):
    def __init__(self, request, code, data=None):
        '''
        Create a Response object.

        Arguments:
        request -- The Request that generated this response.
        code -- The HTTP response code to be returned.
        data -- Data that should be attached to this response.
        '''
        self.request = request
        self.code = code
        self.data = data

    def __bool__(self):
        return self.code in [200, 201]

    @classmethod
    def ok(cls, request, data=None):
        return cls(request, 200, data)

    @classmethod
    def created(cls, request, data=None):
        return cls(request, 201, data)

    @classmethod
    def bad_request(cls, request, data=None):
        return cls(request, 400, data)

    @classmethod
    def forbidden(cls, request, data=None):
        return cls(request, 403, data)

    @classmethod
    def not_found(cls, request, data=None):
        return cls(request, 404, data)

    @classmethod
    def conflict(cls, request, data=None):
        return cls(request, 409, data)

    @classmethod
    def error(cls, request, msg):
        return cls(request, 500, data={'error':msg})


class SleepBaseModel(BaseModel):
    def __new__(cls, name, bases, attrs):
        if not bases:
            return super().__new__(cls, name, bases, attrs)
        else:
            bases += (Model,)

        cls = super().__new__(cls, name, bases, attrs)
        cls._meta.db_table_func = Sleep._table_func
        cls._meta.model_name = Sleep._table_func(cls)

        Sleep._add_model(cls)

        return cls


class SleepModel(metaclass=SleepBaseModel):
    @classmethod
    def key(cls):
        primary_key = cls._meta.primary_key.name
        return getattr(cls, primary_key)

    @classmethod
    def orderfield(cls):
        if 'name' in cls._meta.fields:
            return getattr(cls, 'name')
        else:
            return cls.key()
