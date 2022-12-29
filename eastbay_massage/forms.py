from django.forms import Form, CharField, TextInput
from django.core.validators import EmailValidator

class EmailForm(Form):
    email = CharField(max_length=1024, required=True)
    message = CharField(max_length=30 * 1024, required=True, validators=[EmailValidator(message="Invalid Email")])