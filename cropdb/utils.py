from flask import make_response, render_template, jsonify, request, g, url_for
from peewee import ForeignKeyField, Expression
from urllib.parse import urlparse, parse_qs
from werkzeug.exceptions import NotFound, MethodNotAllowed
from collections import OrderedDict

from cropdb import app


class ResponseError(Exception):
    code = 400
    title = 'Bad request'
    message = 'The server could not handle your request.'

    def __init__(self, code=None, title=None, message=None, data=None):
        super().__init__(self)

        if code:
            self.code = code

        if title:
            self.title = title

        if message:
            self.message = message

        self.data = data

    def to_dict(self):
        d = dict(code=self.code, title=self.title, message=self.message)

        if self.data:
            d['data'] = self.data

        return d


def template(temp, d={}, code=200, allow_json=True):
    want_json = requesting_mime('application/json') or g.fmt_json

    if want_json and allow_json:
        resp = jsonify(**d)
    else:
        resp = render_template(temp, **d)

    return make_response(resp, code)


def requesting_mime(type):
    mimes = [type, 'text/html']
    best = request.accept_mimetypes.best_match(mimes)
    return best == type and \
        request.accept_mimetypes[best] > request.accept_mimetypes['text/html']


def select_filter(sq, and_filters=[], or_filters=[]):
    '''
    Convert a list of filters from a URL querystring to a set of peewee WHERE
    clauses.
    '''
    def get_expression(flt):
        f = flt.split(app.config['FLT_SEP'])

        if len(f) < 3:
            return None

        field, op, value = tuple(f[:3])
        model = sq.model_class
        
        if field not in model._meta.fields:
            return None

        model_field = model._meta.fields[field]

        if isinstance(model_field, ForeignKeyField):
            sq.join(model_field.rel_model)

        attr_field = getattr(model, field)
        exp = None

        if op == 'in':
            value_list = value.split('|')
            exp = (attr_field << value_list)
        elif op == 'eq':
            exp = (attr_field == value)
        elif op == 'neq':
            exp = (attr_field != value)
        elif op == 'gt':
            exp = (attr_field > value)
        elif op == 'gte':
            exp = (attr_field >= value)
        elif op == 'lt':
            exp = (attr_field < value)
        elif op == 'lte':
            exp = (attr_field <= value)

        return exp

    for flt in and_filters:
        exp = get_expression(flt)
        if exp:
            sq = sq.where(exp)

    for flt in or_filters:
        exp = get_expression(flt)
        if exp:
            sq = sq.orwhere(exp)

    return sq

def expression_dict(exp):
    '''
    Translate the _where Expression tree to a dict:
    {field:(op,rhs)}
    '''
    ret = {}

    def rec(d, e):
        if isinstance(e.lhs, Expression):
            d = rec(d, e.lhs)
        else:
            d[e.lhs] = (e.op, e.rhs)

        if isinstance(e.rhs, Expression):
            d = rec(d, e.rhs)

        return d

    ret = rec(ret, exp)
    return ret 


def check_url(url):
    u = urlparse(url)

    try:
        root = app.config.get('SERVER_NAME') or '127.0.0.1'
        adapter = app.url_map.bind(root)
        match = adapter.match(u.path, "GET", query_args=u.query)
        endpoint = match[0]
        args = match[1]
        args.update(parse_qs(u.query))
        url = url_for(endpoint, **args)
    except (NotFound, MethodNotAllowed) as e:
        url = None

    return url


def next_url(default='index'):
    url = None

    if request.referrer:
        url = check_url(request.referrer)

    return url or url_for(default)


def map_query(sq, fname):
    '''
    Map select query results according to unique field.
    ie. convert [[…,field,…],…] → {field:[],…}
    '''
    query_model = sq.model_class
    field = query_model._meta.fields.get(fname)

    if not field:
        raise Exception('No field', fname)

    ret = OrderedDict()

    for row in sq:
        if isinstance(field, ForeignKeyField):
            val = getattr(row, fname).get_name()
        else:
            val = getattr(row, fname)

        if val not in ret:
            ret[val] = []

        ret[val].append(row)

    return ret


@app.template_filter('plural')
def plural_filter(s):
    return s[:-1]+'ies' if s[-1]=='y' else s+'s'

@app.context_processor
def utility_processor():
    return dict(
            map_query=map_query,
            next_url=next_url
            )
