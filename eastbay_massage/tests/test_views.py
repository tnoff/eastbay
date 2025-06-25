from django.test import TestCase, RequestFactory
from django.http import HttpRequest
from django.urls import reverse
from unittest.mock import patch

from eastbay_massage.views import log_csrf_attempt

class CSRFLoggingTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch('eastbay_massage.views.logger')  # Mock the logger to verify calls
    def test_csrf_token_missing_logs_violation(self, mock_logger):
        request = self.factory.post('/fake-url/', data={})  # No csrfmiddlewaretoken
        response = log_csrf_attempt(request)

        self.assertEqual(response.status_code, 403)
        mock_logger.warning.assert_any_call("CSRF violation attempt detected.")
        mock_logger.warning.assert_any_call("IP: %s", request.META.get("REMOTE_ADDR"))
        mock_logger.warning.assert_any_call("Headers: %s", dict(request.headers))
        mock_logger.warning.assert_any_call("POST data: %s", request.POST.dict())