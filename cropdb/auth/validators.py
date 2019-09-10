from wtforms import ValidationError

from cropdb.auth.models import ApdUser


class UniqueEmail(object):
    def __init__(self, message='Invalid email address'):
        self.msg = message

    def __call__(self, form, field):
        try:
            ApdUser.get(ApdUser.email == field.data)
        except ApdUser.DoesNotExist:
            return
        raise ValidationError(self.msg)

class ExistingEmail(object):
    def __init__(self, message='Invalid email address'):
        self.msg = message

    def __call__(self, form, field):
        try:
            ApdUser.get(ApdUser.email == field.data)
        except ApdUser.DoesNotExist:
            raise ValidationError(self.msg)

class MatchField(object):
    def __init__(self, match, message=None):
        self.msg = message
        self.match = match

    def __call__(self, form, field):
        match_field = getattr(form, self.match, None)

        if match_field:
            if match_field.data != field.data:
                if self.msg:
                    msg = self.msg
                else:
                    msg = self.label + ' must match input in ' + match_field.label
                raise ValidationError(msg)

class NotMatchField(object):
    def __init__(self, match, message=None):
        self.msg = message
        self.match = match

    def __call__(self, form, field):
        match_field = getattr(form, self.match, None)

        if match_field:
            if match_field.data == field.data:
                if self.msg:
                    msg = self.msg
                else:
                    msg = self.label + ' must not match input in ' + match_field.label
                raise ValidationError(msg)

