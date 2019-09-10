from itsdangerous import (
        TimedJSONWebSignatureSerializer as Serializer, 
        BadSignature, 
        SignatureExpired
        )
from passlib.utils import generate_password
from datetime import datetime, timezone, timedelta

from cropdb import app


def create_token(data, secret, salt=None, timeout=600):
    '''
    Create a signed token with serialised data.

    Arguments:
    data -- The data to be stored in the token.
    secret -- The application's secret key.
    salt -- An optional salt for namespacing tokens.
    timeout -- The expiry time for this token.
    '''
    s = Serializer(secret, salt=salt, expires_in=timeout)
    return s.dumps(data)

def verify_token(secret, token, salt=None):
    '''Verify a token and return the packed data.'''
    s = Serializer(secret, salt=salt)
    
    try:
        data = s.loads(token)
    except BadSignature:
        return None
    except SignatureExpired:
        return None

    return data

def current_date():
    return datetime.utcnow()

def default_pass(size=100):
    '''Used to generate a new default (unused) password for users.'''
    return generate_password(size)

def set_auth_cookie(response, token, expires):
    response.set_cookie(
            app.config['AUTH_COOKIE'],
            token,
            secure=app.config['AUTH_SECURE'],
            httponly=app.config['AUTH_HTTPONLY'],
            expires=expires
            )
    return response
