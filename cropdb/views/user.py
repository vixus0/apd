from flask import request, g, url_for, redirect

from cropdb import app
from cropdb.utils import ResponseError, template, next_url, check_url
from cropdb.auth.decorators import login_required, csrf_required
from cropdb.auth.models import ApdUser
from cropdb.auth.utils import set_auth_cookie, current_date
from cropdb.auth.forms import (
        LoginForm, ChangePwdForm, ChangeEmailForm, ResetPwdForm
        )


# - user
#   GET:
#       Display user information, provide links to change email/password and 
#       view current subscriptions.
@app.route('/user')
@login_required
def user_profile():
    return g.user.email


# - login
#   GET:
#       Return a login form.
#   POST:
#       Authenticates the user and returns a token in the form of a cookie.
@app.route('/user/login', methods=['GET', 'POST'])
def user_login():
    user = g.get('user', None)

    if user:
        if user.is_authenticated:
            return redirect(url_for('index'))

    form = LoginForm(request.form)

    if request.method == 'POST':
        if form.validate():
            email = form.email.data
            password = form.password.data
            next = check_url(form.next.data) or url_for('index')

            user = ApdUser.verify_user(email, password, attempts=app.config['AUTH_ATTEMPTS'])

            if user:
                token, expires = user.create_session(
                        app.config['SECRET'], 
                        app.config['AUTH_TIMEOUT'], 
                        location=request.remote_addr
                        )
                if token:
                    resp = redirect(next)
                    resp = set_auth_cookie(resp, token, expires)

                    return resp
                else:
                    form.email.errors.append('Could not log in.')
            else:
                form.email.errors.append('Could not log in.')
        else:
            form.email.errors.append('Missing information.')

    form.next.data = next_url()
    return template('login.html', dict(form=form))


# - logout
#   POST:
#       Invalidates current user auth token.
@app.route('/user/logout', methods=['GET', 'POST'])
@csrf_required
def user_logout():
    user = g.get('user', None)

    if request.method == 'GET':
        if user:
            if not user.is_authenticated:
                raise redirect(url_for('index'))
        else:
            return redirect(url_for('index'))
        return template('logout.html')

    elif request.method == 'POST':
        value = request.form.get('confirm')
        next = request.form.get('next')
        next = check_url(next) or url_for('index')

        if value == 'accept':
            g.user.expire_sessions()
            delattr(g, 'user')
            resp = redirect(url_for('index'))
            resp = set_auth_cookie(resp, 'null', current_date())
            return resp
        else:
            return redirect(next)


# - change_password
#   GET:
#       Return a form for the user to assign a new password.
#   POST:
#       Process the password change.
@app.route('/user/change_password', methods=['GET', 'POST'])
@csrf_required
def user_chpass():
    form = ChangePwdForm(request.form)

    if request.method == 'POST' and form.validate():
        old = form.old_password.data
        new = form.new_password.data

        if None in [old,new] or old == new:
            raise ResponseError()

        if not g.user.verify_pass(old):
            raise ResponseError(403, 'Wrong password', 'Please provide your original password.')

        g.user.set_pass(new)
        g.user.expire_sessions()
        delattr(g, 'user')
        resp = redirect(url_for('user_login'))
        resp = set_auth_cookie(resp, 'null', current_date())

        return resp

    return template('change_password.html', dict(form=form))


# - change_email
#   GET:
#       Return a form for the user to assign a new email.
#   POST:
#       Process the email change.
@app.route('/user/change_email', methods=['GET', 'POST'])
@csrf_required
def user_chemail():
    form = ChangeEmailForm(request.form)

    if request.method == 'POST' and form.validate():
        old = form.old_email.data
        new = form.new_email.data
        pwd = form.password.data

        if None in [old,new] or old == new:
            raise ResponseError()

        if old != g.user.email or not g.user.verify_pass(pwd):
            raise ResponseError(403, 'Wrong email or password', 'Please provide your original email and current password.')

        token = g.user.create_reset_token(
                app.config['SECRET'], app.config['RESET_TIMEOUT'], which='email',
                extra={'new_email':new}
                )

        if not token:
            raise ResponseError()

        # email user

        g.user.inactivate()
        delattr(g, 'user')
        resp = template('email_sent.html')
        resp = set_auth_cookie(resp, 'null', current_date())

        return resp

    return template('change_email.html', dict(form=form))


# - reset_password
#   GET:
#       Return form for user to request password change because they have forgotten.
#   POST:
#       Process the change request and create a reset token.
@app.route('/user/reset_password', methods=['GET', 'POST'])
def user_resetpass():
    form = ResetPwdForm(request.form)

    if request.method == 'POST' and form.validate():
        email = form.email.data

        if not email:
            raise ResponseError(400, 'Email required', 'Please provide the email address you use to log in.')

        try:
            user = ApdUser.get(ApdUser.email == email)
        except ApdUser.DoesNotExist:
            user = None

        if user:
            token = user.create_reset_token(
                    app.config['SECRET'], app.config['RESET_TIMEOUT'], which='password'
                    )

            if not token:
                raise ResponseError()

            # email user

        return template('email_sent.html')

    return template('reset_password.html', dict(form=form))
