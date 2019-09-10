'''
    tests
    —————

    User authentication testing.

    :copyright: (c) 2015 by Anshul Sirur.
'''
import time

from cropdb import app
from cropdb.auth.utils import verify_token
from cropdb.tests.test_base import TestBase, get_json, get_string

class TestAuth(TestBase):
    def get_token(self, user, passwd=None):
        '''Obtain a session token.'''
        passwd = passwd if passwd else user._pwd
        rv = self.cli.post('/user/login',
                data={'email':user.email, 'password':passwd}
                )
        return rv

    def chpass(self, old_pwd, new_pwd):
        rv = self.get_token(self.normal, old_pwd)
        self.assertEqual(200, rv.status_code)
        token = rv.headers['Set-Cookie'].split(';')[0].split('=')[1]
        data = verify_token(app.config['SECRET'], token, salt='session')
        csrf = data['csrf']

        # Change password
        rv = self.cli.post('/user/change_password',
                data={
                    'old_password':old_pwd, 
                    'new_password':new_pwd, 
                    'confirm_password':new_pwd,
                    '_check':csrf
                    }
                )
        self.assertEqual(200, rv.status_code)

    def test_session_lifecycle(self):
        # Get session token
        rv = self.get_token(self.normal)
        self.assertEqual(200, rv.status_code)
        
        # Use token to view user info
        rv = self.cli.get('/user')
        data = get_string(rv)
        self.assertEqual(self.normal.email, data)

        # Expire sessions
        rv = self.cli.post('/user/logout')
        self.assertEqual(200, rv.status_code)

        # Try using token again
        rv = self.cli.get('/user')
        self.assertEqual(rv.status_code, 403)

    def test_session_timeout(self):
        # Set a shorter timeout
        test_timeout = 2
        orig_timeout = app.config['AUTH_TIMEOUT']
        app.config['AUTH_TIMEOUT'] = test_timeout

        # Get session token
        rv = self.get_token(self.normal)
        self.assertEqual(200, rv.status_code)

        # Wait
        time.sleep(test_timeout + 1)

        # Try using token again
        rv = self.cli.get('/user')
        self.assertEqual(rv.status_code, 403)

        # Reset timeout
        app.config['AUTH_TIMEOUT'] = orig_timeout

    def test_repeat_auth(self):
        # Get token
        rv = self.get_token(self.normal)
        self.assertEqual(200, rv.status_code)
        a_cookie = rv.headers['Set-Cookie']

        # Try again
        rv = self.get_token(self.normal)
        self.assertEqual(200, rv.status_code)

    def test_wrong_password(self):
        rv = self.get_token(self.normal, passwd='wrong')
        self.assertEqual(403, rv.status_code)

    def test_login_attempts(self):
        for i in range(app.config['AUTH_ATTEMPTS']):
            rv = self.get_token(self.normal, passwd='wrong')
            self.assertEqual(403, rv.status_code)

        # Should be banned
        rv = self.get_token(self.normal)
        self.assertEqual(403, rv.status_code)

        # Reset
        self.normal.unban()

    def test_banned_user(self):
        rv = self.get_token(self.banned)
        self.assertEqual(403, rv.status_code)

    def test_inactive_User(self):
        rv = self.get_token(self.inactive)
        self.assertEqual(403, rv.status_code)

    def test_admin_required(self):
        users = [self.admin, self.normal]

        for user in users:
            rv = self.get_token(user)
            self.assertEqual(200, rv.status_code, 'Failed login: '+user.email)
            rv = self.cli.get('/admin')
            if user is self.admin:
                self.assertEqual(200, rv.status_code)
            else:
                self.assertEqual(404, rv.status_code)

            # Expire sessions
            rv = self.cli.post('/user/logout')
            self.assertEqual(200, rv.status_code)

    def test_ban_during_auth(self):
        # Get token
        rv = self.get_token(self.normal)
        self.assertEqual(200, rv.status_code)

        # Ban user
        self.normal.ban()

        # Use token to view user info
        rv = self.cli.get('/user')
        self.assertEqual(403, rv.status_code)

        # Unban user
        self.normal.unban()

    def test_chpass_during_auth(self):
        old_pwd = self.normal._pwd
        new_pwd = 'newpass'
        self.chpass(old_pwd, new_pwd)

        # Use token to view user info
        rv = self.cli.get('/user')
        self.assertEqual(403, rv.status_code)

        self.chpass(new_pwd, old_pwd)

        # Try again - should still not work
        rv = self.cli.get('/user')
        self.assertEqual(403, rv.status_code)
