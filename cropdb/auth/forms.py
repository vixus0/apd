from wtforms import (
        validators as val,
        Form,
        StringField, PasswordField, HiddenField, SubmitField
        )

from cropdb.auth.validators import *


class LoginForm(Form):
    email = StringField('Email', [val.InputRequired(), val.Email()])
    password = PasswordField('Password', [val.InputRequired()])
    next = HiddenField('Next')

class ResetPwdForm(Form):
    email = StringField('Email', [val.InputRequired(), val.Email(), ExistingEmail()])

class ActivateUserForm(Form):
    password = PasswordField('Password', [val.InputRequired()])
    confirm_password = PasswordField('Confirm New Password', [val.InputRequired(), MatchField('new_password', 'Please confirm password')])

class ChangePwdForm(Form):
    old_password = PasswordField('Old Password', [val.InputRequired()])
    new_password = PasswordField('New Password', [val.InputRequired(), NotMatchField('old_password', 'New password must be different from old one')])
    confirm_password = PasswordField('Confirm New Password', [val.InputRequired(), MatchField('new_password', 'Please confirm password')])

class ChangeEmailForm(Form):
    old_email = StringField('Old Email', [val.InputRequired(), val.Email()])
    new_email = StringField('New Email', [val.InputRequired(), UniqueEmail()])
    password = PasswordField('Password', [val.InputRequired()])

class CreateUserForm(Form):
    new_email = StringField('Email', [val.InputRequired(), val.Email()])
    new_password = PasswordField('Password')
