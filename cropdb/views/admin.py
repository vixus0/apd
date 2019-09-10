from flask import request, jsonify

from cropdb import app, resources, sub_resources
from cropdb.utils import template, ResponseError
from cropdb.auth.decorators import admin_required, csrf_required
from cropdb.auth.models import ApdUser, Session, Subscription
from cropdb.auth.forms import CreateUserForm
from cropdb.auth.utils import current_date

# - admin
#   GET:
#       Display admin control panel.
@app.route('/admin')
@admin_required
def admin():
    return template('admin.html')


# - users
#   GET:
#       Display list of users.
@app.route('/admin/users', methods=['GET', 'POST'])
@admin_required
@csrf_required
def admin_users():
    '''(ADMIN) List all users.'''

    create_form = CreateUserForm(request.form)

    # List users
    user_rows = ApdUser.select().order_by(
            ApdUser.admin.desc(), ApdUser.orderfield()
            )
    users = []

    for u in user_rows:
        users.append(dict(
            id = u.get_key(),
            email = u.email,
            active = u.active,
            banned = u.banned,
            admin = u.admin,
            wrong_logins = u.wrong_logins
            ))

    new_user = None

    if request.method == 'POST':
        # Create new user
        if create_form.validate():
            email = create_form.new_email.data
            password = create_form.new_password.data
            new_user, created = ApdUser.get_or_create(email=email)

            if created and password:
                new_user.set_pass(password)

            if not created:
                create_form.new_email.errors.append('User already exists.')
                new_user = None

    return template(
            'admin_users.html', 
            dict(users=users, create_form=create_form, new_user=new_user)
            )



# - single_user
@app.route('/admin/users/<user_id>', methods=['GET', 'DELETE', 'PUT'])
@admin_required
def admin_single_user(user_id):
    try:
        user = ApdUser.get(ApdUser.keyfield() == user_id)
    except ApdUser.NotFound:
        raise ResponseError(404, 'No such user')

    if request.method == 'GET':
        # Get user info
        sub_res = {}

        for r in sub_resources:
            model = resources[r]
            rows = model\
                    .select(model.keyfield(), model.orderfield())\
                    .order_by(model.orderfield())

            sub_res[r] = []

            for row in rows:
                sub_res[r].append({
                    'id' : row.get_id(),
                    'name' : row.get_name(),
                    })

        d = dict(user=user, sub=sub_res, sub_keys=sub_resources)

        return template('admin_single_user.html', d)

    elif request.method == 'PUT':
        # Update user
        dat = request.get_json(silent=True)

        if dat:
            action = dat['action']

            if action == 'activate':
                user.activate()
            elif action == 'inactivate':
                user.inactivate()
            elif action == 'ban':
                user.ban()
            elif action == 'unban':
                user.unban()

            status = {
                    'active':user.active, 
                    'banned':user.banned, 
                    'banned_date':user.banned_date if user.banned_date else 'None'
                    }

            return jsonify(success=True, status=status)
        else:
            raise ResponseError()

    elif request.method == 'DELETE':
        # Remove user
        pass


# - subscriptions
@app.route('/admin/subs/<user_id>', methods=['GET', 'PUT'])
@admin_required
def admin_subs(user_id, resource=None, res_id=None):
    try:
        user = ApdUser.get(ApdUser.keyfield() == user_id)
    except ApdUser.NotFound:
        raise ResponseError(404, 'No such user')

    if request.method == 'GET':
        # Return user's subscriptions
        sub_rows = Subscription.select().where(
                (Subscription.user == user) &
                (Subscription.resource << sub_resources)
                )

        subs = {res:{'all':False,'idx':[]} for res in sub_resources}
        min_id = {res:0 for res in sub_resources}

        for row in sub_rows:
            min_id[row.resource] = min(min_id[row.resource], row.resource_id)
            days_left = max(0, (row.expires - current_date()).days)
            subs[row.resource]['idx'].append({
                'id' : row.resource_id,
                'expires_in' : days_left
                })

        for res in sub_resources:
            subs[res]['all'] = min_id[res] == -1

        return jsonify(subscriptions=subs)

    elif request.method == 'PUT':
        # Update user's subscriptions
        dat = request.get_json(silent=True)

        if dat:
            ret = Subscription.change(user, dat['subscriptions'], dat['extend_days'])

            if ret:
                return jsonify(updated=ret)
            else:
                raise ResponseError()

        else:
            raise ResponseError()


# - sessions
#   GET:
#       Display user session logs.
@app.route('/admin/sessions')
@app.route('/admin/sessions/<a>')
@admin_required
def admin_sessions(a=''):
    '''(ADMIN) List user sessions.'''

    session_rows = Session.select().join(ApdUser)\
        .order_by(Session.start_time.desc())\
        .limit(100)

    if a == 'active':
        session_rows = session_rows.where(Session.active == True)

    user = request.args.get('user')

    if user:
        session_rows = session_rows.where(Session.user == user)

    sessions = []

    for s in session_rows:
        sessions.append(dict(
            user = s.user.get_key(),
            email = s.user.email,
            start_time = str(s.start_time),
            end_time = str(s.end_time),
            active = s.active,
            location = s.location
            ))

    return template('admin_sessions.html', dict(sessions=sessions))
