from mongoengine import Document, StringField, BooleanField

class User(Document):
    username = StringField(required=True, unique=True)
    password = StringField(required=True) 
    display_name = StringField()
    must_change_password = BooleanField(default=True)
