from peewee import *
from passlib.apps import custom_app_context
from datetime import timedelta

from cropdb import BaseModel, db
from cropdb.auth.utils import create_token, verify_token, current_date, default_pass

class ApdUser(BaseModel):
    '''A client using the database.'''
    email = CharField(unique=True)
    phash = CharField(default=default_pass, max_length=128)
    csrf = CharField(null=True)
    created_date = DateTimeField(default=current_date)
    banned_date = DateTimeField(null=True)
    active = BooleanField(default=False)
    banned = BooleanField(default=False)
    admin = BooleanField(default=False)
    wrong_logins = IntegerField(default=0)
    reset = CharField(null=True)

    def set_pass(self, password):
        '''Set the password hash from a cleartext password.'''
        self.expire_sessions()
        self.phash = custom_app_context.encrypt(password)
        self.save()

    def verify_pass(self, password):
        '''Verify a cleartext password against the stored hash.'''
        return custom_app_context.verify(password, self.phash)

    def create_reset_token(self, secret, timeout, which='email', extra=None):
        '''Creates a new reset token (email or password reset).'''
        if self.banned or not self.active:
            return None

        self.expire_sessions()

        if self.reset:
            data = verify_token(secret, self.reset, salt='reset')
            if data:
                # Token still valid
                return None

        data = {'user':self.id, 'which':which}

        if extra:
            data.update(extra)

        token = create_token(data, secret, salt='reset', timeout=timeout)

        self.reset = token
        self.save()

        return token

    def create_session(self, secret, timeout, location):
        '''Create a new session for this user.'''
        if not self.is_active:
            return None

        currt = current_date()
        endt = currt + timedelta(seconds=timeout)

        self.expire_sessions()

        session = Session.create(
                user=self, 
                location=location, 
                start_time=currt, 
                end_time=endt
                )

        data = {'session':session.id}
        token = create_token(data, secret, salt='session', timeout=timeout)

        return token, endt

    def refresh_session(self, secret, timeout):
        '''Extend the current active session.'''
        if not (self.active_session and self.is_active):
            return None

        currt = current_date()
        endt = currt + timedelta(seconds=timeout)

        active_session = self.active_session

        if currt >= active_session.end_time:
            return None

        data = {'session':active_session.id}
        token = create_token(data, secret, salt='session', timeout=timeout)

        active_session.end_time = endt
        active_session.save()

        return token, endt

    def expire_sessions(self):
        '''Expire all previous sessions.'''
        currt = current_date()
        query = Session.update(active = False, end_time = currt)\
                       .where((Session.user == self) & (Session.active == True))
        query.execute()

    def ban(self):
        '''Ban this user.'''
        if not self.banned:
            self.expire_sessions()
            self.banned = True
            self.banned_date = current_date()
            self.save()

    def unban(self):
        '''Unban user.'''
        if self.banned:
            self.banned = False
            self.banned_date = None
            self.save()

    def activate(self):
        '''Activate user.'''
        if not self.active:
            self.active = True
            self.save()

    def inactivate(self):
        '''Inactivate this user (for pwd/email resets).'''
        if self.active:
            self.expire_sessions()
            self.active = False
            self.save()

    @property
    def active_session(self):
        try:
            session = Session.get(Session.user == self, Session.active == True)
        except Session.DoesNotExist:
            session = None
        return session

    @property
    def is_authenticated(self):
        return self.is_active and self.active_session != None

    @property
    def is_active(self):
        return self.active == True and self.banned == False

    @property
    def is_anonymous(self):
        return False

    @property
    def is_admin(self):
        return self.admin

    def get_auth_token(self):
        return self.active_session.token.encode('utf8')

    def get_id(self):
        return str(self.id).encode('utf8')
    

    # Static methods
    @staticmethod
    def verify_session(secret, token):
        '''Check the token matches an active session and return the user.'''
        data = verify_token(secret, token, salt='session')

        if data is None:
            return None

        session_id = data['session']

        try:
            session = Session.get(
                    Session.id == session_id,
                    Session.active == True
                    )
        except Session.DoesNotExist:
            return None

        user = session.user

        if not user.is_authenticated:
            return None

        return user

    @staticmethod
    def register_user(email):
        '''Register a new user.'''
        return ApdUser.get_or_create(email=email)

    @staticmethod
    def verify_user(email, password, attempts=20):
        '''Verify a user's login credentials and return the associated object.'''
        try:
            user = ApdUser.get(ApdUser.email == email)
        except ApdUser.DoesNotExist:
            return None

        if not user.is_active:
            return None

        if not user.verify_pass(password):
            user.wrong_logins = user.wrong_logins + 1
            user.save()

            if user.wrong_logins >= attempts:
                user.ban()

            return None

        user.wrong_logins = 0
        user.save()

        return user

    @staticmethod
    def verify_reset_token(secret, token, which='email'):
        data = verify_token(secret, token, salt='reset')

        if data:
            t_user = data['user']
            t_which = data['which']
        else:
            return None

        if which != t_which:
            return None

        try:
            user = ApdUser.get(ApdUser.id == t_user)
        except ApdUser.DoesNotExist:
            return None

        if not user.is_active:
            return None

        return user


class Session(BaseModel):
    '''Stores session information per user.'''
    user = ForeignKeyField(ApdUser, related_name='sessions')
    start_time = DateTimeField(default=current_date)
    end_time = DateTimeField()
    active = BooleanField(default=True)
    location = CharField()


class Subscription(BaseModel):
    '''Stores resources user has permission to access.'''
    user = ForeignKeyField(ApdUser, related_name='subscriptions')
    resource = CharField()
    resource_id = IntegerField()
    can_put = BooleanField(default=False)
    expires = DateTimeField()

    class Meta:
        indexes = (
                # resource+resource_id should be unique
                (('user', 'resource', 'resource_id'), True),
                )

    @classmethod
    def change(cls, user, res_idx, days=30):
        '''Update subscriptions for the given user.'''
        cdate = current_date()
        expires_at = cdate + timedelta(days=days)
        updated = {}

        with db.atomic():
            for res, idx in res_idx.items():
                flt = (cls.user == user) & (cls.resource == res)

                # Delete rows if not in idx
                dq = cls.delete().where(
                        flt & 
                        (cls.resource_id.not_in(idx))
                        )
                dq.execute()

                # Select remaining rows
                sq = cls.select(cls.resource_id).where(flt).tuples()
                sq = [i[0] for i in sq]

                # Update expiry time
                uq = cls.update(expires=expires_at).where(flt).execute()

                # Insert new rows
                data_src = []
                upd_idx = []
                
                for id in idx:
                    id = int(id)
                    if id not in sq:
                        data_src.append({
                            'user':user, 
                            'resource':res, 
                            'resource_id':id, 
                            'expires':expires_at
                            })
                        upd_idx.append(id)

                if len(data_src) > 0:
                    cls.insert_many(data_src).execute()

                updated[res] = upd_idx

        return updated


    @classmethod
    def available_items(cls, user, resource):
        items = cls\
                .select(
                    cls.resource_id,
                    )\
                .where(
                    cls.user == user,
                    cls.resource == resource,
                    cls.expires >= current_date(),
                    )

        return items

    @classmethod
    def can_access(cls, user, resource, rid):
        items = cls.available_items(user, resource)
        items = items.where(cls.resource_id == rid)
        return items.count() == 1
