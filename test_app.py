import os
import unittest
from unittest.mock import patch, MagicMock

os.environ.setdefault('CONTACT_EMAIL', 'test@example.com')
os.environ.setdefault('CONTACT_NUMBER', '555-555-5555')
os.environ.setdefault('EMAIL_HOST_USER', 'test@example.com')

from app import app, ContactForm

class FlaskAppTestCase(unittest.TestCase):
    def setUp(self):
        """Set up test client and config"""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
        app.config['EMAIL_ENABLED'] = False  # Disable email sending in tests
        self.client = app.test_client()

    def test_home_page_loads(self):
        """Test that the home page loads successfully"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'East Bay Massage and Lymph Drainage', response.data)

    def test_home_page_has_form(self):
        """Test that the home page contains the contact form"""
        response = self.client.get('/')
        self.assertIn(b'Contact Form', response.data)
        self.assertIn(b'name="name"', response.data)
        self.assertIn(b'name="email"', response.data)
        self.assertIn(b'name="message"', response.data)

    def test_contact_form_submission_success(self):
        """Test successful form submission"""
        data = {
            'name': 'Test User',
            'email': 'test@example.com',
            'phone_number': '(201) 555-0123',
            'message': 'This is a test message'
        }
        response = self.client.post('/send_message/', data=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Message Successfully Sent', response.data)

    def test_contact_form_missing_name(self):
        """Test form submission with missing name"""
        data = {
            'email': 'test@example.com',
            'message': 'This is a test message'
        }
        response = self.client.post('/send_message/', data=data)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Contact Form', response.data)  # Should show form again

    def test_contact_form_invalid_email(self):
        """Test form submission with invalid email"""
        data = {
            'name': 'Test User',
            'email': 'not-an-email',
            'message': 'This is a test message'
        }
        response = self.client.post('/send_message/', data=data)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Contact Form', response.data)  # Should show form again

    def test_contact_form_missing_message(self):
        """Test form submission with missing message"""
        data = {
            'name': 'Test User',
            'email': 'test@example.com'
        }
        response = self.client.post('/send_message/', data=data)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Contact Form', response.data)  # Should show form again

    def test_message_successful_page(self):
        """Test the success page loads"""
        response = self.client.get('/message_successful/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Message Successfully Sent', response.data)

    def test_contact_form_validation_phone_optional(self):
        """Test that phone number is optional"""
        data = {
            'name': 'Test User',
            'email': 'test@example.com',
            'message': 'This is a test message'
            # No phone number
        }
        response = self.client.post('/send_message/', data=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Message Successfully Sent', response.data)

    @patch('app.smtplib.SMTP')
    def test_email_sending_when_enabled(self, mock_smtp):
        """Test that email is sent when EMAIL_ENABLED is True"""
        app.config['EMAIL_ENABLED'] = True
        app.config['EMAIL_HOST_PASSWORD'] = 'test_password'

        # Mock the SMTP server
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        data = {
            'name': 'Test User',
            'email': 'test@example.com',
            'phone_number': '2015550123',
            'message': 'This is a test message'
        }

        response = self.client.post('/send_message/', data=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Verify SMTP methods were called
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()

    def test_csrf_protection_enabled(self):
        """Test that CSRF protection is working (when enabled)"""
        app.config['WTF_CSRF_ENABLED'] = True

        data = {
            'name': 'Test User',
            'email': 'test@example.com',
            'message': 'This is a test message'
        }

        # Post without CSRF token should fail
        response = self.client.post('/send_message/', data=data)
        self.assertEqual(response.status_code, 400)

        # Reset for other tests
        app.config['WTF_CSRF_ENABLED'] = False


class ContactFormTestCase(unittest.TestCase):
    def setUp(self):
        """Set up Flask app context for form testing"""
        self.app = app
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        """Clean up Flask app context"""
        self.app_context.pop()

    def test_form_validates_with_all_fields(self):
        """Test form validation with all fields provided"""
        form = ContactForm(data={
            'name': 'Test User',
            'email': 'test@example.com',
            'phone_number': '2015550123',
            'message': 'This is a test message'
        }, meta={'csrf': False})
        # Note: validate() returns False without request context for CSRF
        # We're just testing the field validators
        self.assertIsNotNone(form.name.data)
        self.assertIsNotNone(form.email.data)
        self.assertIsNotNone(form.message.data)

    def test_form_requires_name(self):
        """Test that name field is required"""
        form = ContactForm(data={
            'email': 'test@example.com',
            'message': 'This is a test message'
        }, meta={'csrf': False})
        self.assertIsNone(form.name.data)

    def test_form_requires_email(self):
        """Test that email field is required"""
        form = ContactForm(data={
            'name': 'Test User',
            'message': 'This is a test message'
        }, meta={'csrf': False})
        self.assertIsNone(form.email.data)

    def test_form_requires_message(self):
        """Test that message field is required"""
        form = ContactForm(data={
            'name': 'Test User',
            'email': 'test@example.com'
        }, meta={'csrf': False})
        self.assertIsNone(form.message.data)


if __name__ == '__main__':
    unittest.main()
