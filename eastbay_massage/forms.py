from django.forms import Form, CharField, TextInput
from django.core.validators import EmailValidator

from phonenumber_field.formfields import PhoneNumberField

class EmailForm(Form):
    email = CharField(max_length=1024, required=True, validators=[EmailValidator(message="Invalid Email")])
    message = CharField(max_length=30 * 1024, required=True)
    name = CharField(max_length=1024, required=True)
    phone_number = PhoneNumberField(required=False)