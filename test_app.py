import os
import unittest
from unittest.mock import patch, MagicMock

os.environ.setdefault('CONTACT_EMAIL', 'test@example.com')
os.environ.setdefault('CONTACT_NUMBER', '555-555-5555')
os.environ.setdefault('EMAIL_HOST_USER', 'test@example.com')

from opentelemetry import trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from app import app, ContactForm, rename_unrouted_span

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


class UnroutedSpanNamingTestCase(unittest.TestCase):
    """Span names for unmatched routes must not carry the request path.

    The Flask instrumentation falls back to the raw path when no route
    matches, so scanner traffic against a public site produces unbounded
    span names, which become unbounded spanmetrics series downstream.

    These assert on spans captured from the real tracer provider rather
    than on a patched trace.get_current_span. The instrumentation calls
    get_current_span itself to find the parent, so patching it globally
    makes the server span fail to start and the test passes or fails
    depending on suite ordering rather than on the code under test.
    """

    @classmethod
    def setUpClass(cls):
        # The app sets the global provider at import; add a second,
        # synchronous processor to it so spans are readable immediately
        # instead of on the BatchSpanProcessor's flush interval.
        cls.exporter = InMemorySpanExporter()
        trace.get_tracer_provider().add_span_processor(
            SimpleSpanProcessor(cls.exporter)
        )

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        self.exporter.clear()

    def _server_span(self):
        """The single span produced by one request through the test client."""
        spans = self.exporter.get_finished_spans()
        self.assertEqual(len(spans), 1, f'expected 1 span, got {len(spans)}')
        return spans[0]

    def test_unrouted_request_collapses_span_name(self):
        """A 404 is renamed to the constant and keeps the path as an attribute"""
        response = self.client.get('/.aws/credentials')
        # after_request must actually run for 404s, otherwise the rename
        # never happens and the whole fix is inert.
        self.assertEqual(response.status_code, 404)
        span = self._server_span()
        self.assertEqual(span.name, 'HTTP GET <unrouted>')
        self.assertEqual(
            span.attributes['http.unrouted_target'], '/.aws/credentials'
        )

    def test_unrouted_requests_share_one_span_name(self):
        """Distinct probe paths must collapse to the same name, not N names"""
        for path in ('/.env', '/.git/config', '/wp-admin/setup-config.php'):
            self.client.get(path)
        names = {span.name for span in self.exporter.get_finished_spans()}
        self.assertEqual(names, {'HTTP GET <unrouted>'})

    def test_unrouted_span_name_tracks_method(self):
        """The method stays in the name; it is bounded, unlike the path"""
        self.client.post('/.aws/credentials')
        self.assertEqual(self._server_span().name, 'HTTP POST <unrouted>')

    def test_routed_request_keeps_instrumentation_span_name(self):
        """A matched route must keep the name the instrumentation gave it

        Uses / rather than /health: /health is excluded from tracing
        entirely (see ExcludedUrlsTestCase), so it produces no span to
        assert a name on.
        """
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        span = self._server_span()
        self.assertNotEqual(span.name, 'HTTP GET <unrouted>')
        self.assertNotIn('http.unrouted_target', span.attributes)

    def test_non_recording_span_is_left_alone(self):
        """No recording span in flight is not an error"""
        span = MagicMock()
        span.is_recording.return_value = False
        response = MagicMock()
        with app.test_request_context('/.aws/credentials'):
            with patch('app.trace.get_current_span', return_value=span):
                self.assertIs(rename_unrouted_span(response), response)
        span.update_name.assert_not_called()
        span.set_attribute.assert_not_called()


class ExcludedUrlsTestCase(unittest.TestCase):
    """/health must serve normally but produce no span at all.

    The kubelet probes it every few seconds and nothing else calls it, so
    at ~330 probes per real page view it was the site's entire trace
    output. Asserting on spans from the real provider, for the same
    reason UnroutedSpanNamingTestCase does.
    """

    @classmethod
    def setUpClass(cls):
        cls.exporter = InMemorySpanExporter()
        trace.get_tracer_provider().add_span_processor(
            SimpleSpanProcessor(cls.exporter)
        )

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        self.exporter.clear()

    def test_health_still_serves(self):
        """Excluding it from tracing must not affect the response"""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b'OK')

    def test_health_produces_no_span(self):
        """The probe endpoint is not traced"""
        self.client.get('/health')
        self.assertEqual(self.exporter.get_finished_spans(), ())

    def test_other_routes_are_still_traced(self):
        """The exclusion must not disable tracing generally"""
        self.client.get('/')
        self.assertEqual(len(self.exporter.get_finished_spans()), 1)

    def test_pattern_is_anchored_to_the_end(self):
        """A path that merely starts with /health stays traced

        EXCLUDED_URLS ends in $ precisely so a future /health-tips page
        is not silently untraceable.
        """
        self.client.get('/health-tips')
        self.assertEqual(len(self.exporter.get_finished_spans()), 1)


if __name__ == '__main__':
    unittest.main()
