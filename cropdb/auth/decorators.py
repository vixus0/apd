from functools import wraps
from flask import g, request, redirect, url_for

from cropdb.utils import ResponseError
from cropdb.auth.utils import default_pass, current_date


def login_required(f, code=403):
    @wraps(f)
    def decorated_f(*args, **kw):
        if 'user' in g:
            if not g.user.is_authenticated:
                return redirect(url_for('user_login'), code)
        else:
            return redirect(url_for('user_login'), code)
        return f(*args, **kw)
    return decorated_f

def csrf_required(f):
    @wraps(f)
    def decorated_f(*args, **kw):
        if request.method == 'POST':
            print('CHECKING CSRF')
            session_csrf = g.user.csrf
            form_csrf = request.form.get('_check') 
            print('session:', session_csrf, 'form:', form_csrf)
            if None in [session_csrf, form_csrf] or form_csrf != session_csrf:
                raise ResponseError(403, 'CSRF Error')
        elif request.method == 'GET':
            print('GENERATING CSRF')
            g.user.csrf = default_pass()
            g.user.save()
            print(g.user.csrf)
        return f(*args, **kw)
    return login_required(decorated_f, code=404)

def admin_required(f):
    @wraps(f)
    def decorated_f(*args, **kw):
        if g.user.is_admin == False:
            raise ResponseError(404, 'Not found', 'Page not found.')
        return f(*args, **kw)
    return login_required(decorated_f, code=404)
