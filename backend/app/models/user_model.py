from mongoengine import BooleanField, DateTimeField, Document, StringField

class User(Document):
    username = StringField(required=True, unique=True)
    password = StringField(required=True)
    display_name = StringField()
    must_change_password = BooleanField(default=True)
    session_token_hash = StringField(required=False, null=True)
    session_expires_at = DateTimeField(required=False, null=True)
