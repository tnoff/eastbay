from django.test import TestCase
from eastbay_massage.forms import EmailForm

class EmailFormTest(TestCase):

    def test_valid_form_with_all_fields(self):
        data = {
            'email': 'test@example.com',
            'message': 'This is a test message.',
            'name': 'John Doe',
            'phone_number': '+14155552671'
        }
        form = EmailForm(data=data)
        self.assertTrue(form.is_valid())

    def test_valid_form_without_phone_number(self):
        data = {
            'email': 'test@example.com',
            'message': 'This is a test message.',
            'name': 'Jane Doe',
        }
        form = EmailForm(data=data)
        self.assertTrue(form.is_valid())

    def test_missing_required_fields(self):
        data = {
            'email': '',
            'message': '',
            'name': '',
        }
        form = EmailForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertIn('message', form.errors)
        self.assertIn('name', form.errors)

    def test_invalid_email(self):
        data = {
            'email': 'not-an-email',
            'message': 'Message',
            'name': 'Tester',
        }
        form = EmailForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertIn('Invalid Email', form.errors['email'])

    def test_invalid_phone_number(self):
        data = {
            'email': 'test@example.com',
            'message': 'Message',
            'name': 'Tester',
            'phone_number': 'notaphone'
        }
        form = EmailForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('phone_number', form.errors)
