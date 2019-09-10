from flask import request, g, url_for

from cropdb import app, db, link_resources
from cropdb.utils import template, ResponseError
from cropdb.auth.models import ApdUser
from cropdb.auth.utils import default_pass, set_auth_cookie


# -- Debugging
@app.before_request
def debug_request():
    if app.debug and app.config['DEBUG_PRINT']:
        print('-----------:-----------------------')
        print('pre-request: REQ ', request.method, request.path)
        print('pre-request: REM ', request.remote_addr)
        print('           : HED ')
        print(request.headers)
        print('           : COO ', request.cookies)
        print('           : ARG ', request.args)
        print('           : FRM ', request.form)
        print('           : / pre-request --------\n')


@app.after_request
def debug_response(response):
    if app.debug and app.config['DEBUG_PRINT']:
        print('end-request: STA ', response.status_code, response.status)
        print('           : MIM ', response.mimetype)
        print('           : HED ', response.headers)
        #print('           : DAT ', response.data)
        print('           : / end-request --------\n')
    return response


@app.teardown_request
def debug_teardown(exception):
    if app.debug and app.config['DEBUG_PRINT']:
        print('teardown   : ')
        print('-----------:-----------------------\n\n')


# -- Lifecycle
@app.before_request
def database_prepare():
    db.connect()


@app.before_request
def wants_json():
    if request.args.get('fmt') == 'json':
        g.fmt_json = True
    else:
        g.fmt_json = False


@app.before_request
def authenticate_user():
    if 'user' not in g:
        auth = request.authorization

        if auth:
            token = auth.username
        else:
            token = request.cookies.get(app.config['AUTH_COOKIE'])

        if token:
            user = ApdUser.verify_session(app.config['SECRET'], token)
            if user:
                g.user = user


@app.before_request
def generate_links():
    resource_links = []

    for resource in sorted(link_resources.keys()):
        text = resource.replace('_', ' ').title()
        href = url_for('apd_list', resource=resource)
        resource_links.append({ 'rel':resource, 'text':text, 'href':href })

    user_links = {
            'login' : {'text':'Login', 'href':url_for('user_login')},
            'logout' : {'text':'Logout', 'href':url_for('user_logout')},
            'profile' : {'text':'Profile', 'href':url_for('user_profile')},
            'resetpass' : {'text':'Reset Password', 'href':url_for('user_resetpass')},
            }

    g.links = {'resources':resource_links, 'user':user_links}


@app.after_request
def user_refresh(response):
    if 'user' in g:
        rv = g.user.refresh_session(app.config['SECRET'], app.config['AUTH_TIMEOUT'])
        if rv:
            token, expires = rv
            response = set_auth_cookie(response, token, expires)

    return response


@app.teardown_request
def database_teardown(exception):
    if not db.is_closed():
        db.close()


@app.errorhandler(ResponseError)
def handle_response_error(error):
    return template('error.html', {'error':error.to_dict()}, code=error.code)
