"""smoke/site_smoke.py against the real app on a local port: the whole path a deploy depends on.

The smoke test is only worth running in prod if it passes against a healthy app and fails, loudly and
without posting, against a broken one. Both are tested here with a real HTTP server, since the script
speaks urllib and cookies, which a Flask test client would not exercise.
"""
import contextlib
import io
import os
import sys
import threading
import unittest
from unittest.mock import patch, MagicMock

os.environ.setdefault('FLASK_SECRET_KEY', 'test')
os.environ.setdefault('CONTACT_EMAIL', 'test@example.com')
os.environ.setdefault('CONTACT_NUMBER', '555-555-5555')
os.environ.setdefault('EMAIL_HOST_USER', 'test@example.com')

from werkzeug.serving import make_server

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'smoke'))
import site_smoke  # noqa: E402  pylint: disable=wrong-import-position

from app import app  # noqa: E402  pylint: disable=wrong-import-position

MARKER = 'smoke-test@example.com'


def run_smoke(base, email=MARKER, extra=()):
    out = io.StringIO()
    env = {'SMOKE_BASE_URL': base, 'SMOKE_TEST_EMAIL': email, 'SMOKE_TRIES': '1', 'SMOKE_TIMEOUT': '3'}
    with patch.dict(os.environ, env), contextlib.redirect_stdout(out):
        code = site_smoke.main(list(extra))
    return code, out.getvalue()


class SmokeAgainstLocalServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = False
        app.config['WTF_CSRF_ENABLED'] = True
        cls.server = make_server('127.0.0.1', 0, app, threaded=True)
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        app.config['SMOKE_TEST_EMAIL'] = MARKER
        app.config['EMAIL_ENABLED'] = True
        app.config['EMAIL_HOST_PASSWORD'] = 'test_password'

    def tearDown(self):
        app.config['SMOKE_TEST_EMAIL'] = None
        app.config['EMAIL_ENABLED'] = False

    @patch('app.smtplib.SMTP')
    def test_healthy_app_passes_and_sends_nothing(self, mock_smtp):
        code, out = run_smoke(self.base)
        self.assertEqual(code, 0, out)
        self.assertIn('9/9 checks passed', out)
        mock_smtp.assert_not_called()

    @patch('app.smtplib.SMTP')
    def test_server_without_the_setting_is_never_posted_to(self, mock_smtp):
        """The guard: no announcement means no submission, so no real email, and the run fails"""
        app.config['SMOKE_TEST_EMAIL'] = None
        mock_smtp.return_value.__enter__.return_value = MagicMock()
        code, out = run_smoke(self.base)
        self.assertEqual(code, 1)
        self.assertIn('NOT submitting the form', out)
        mock_smtp.assert_not_called()

    @patch('app.smtplib.SMTP')
    def test_server_announcing_a_different_address_is_never_posted_to(self, mock_smtp):
        code, out = run_smoke(self.base, email='other@example.com')
        self.assertEqual(code, 1)
        self.assertIn('NOT submitting the form', out)
        mock_smtp.assert_not_called()

    def test_nothing_listening_fails_every_check(self):
        code, out = run_smoke('http://127.0.0.1:9')
        self.assertEqual(code, 1)
        self.assertIn('0/', out.splitlines()[-1])

    def test_csrf_disabled_server_fails_the_missing_token_check(self):
        app.config['WTF_CSRF_ENABLED'] = False
        try:
            code, out = run_smoke(self.base)
        finally:
            app.config['WTF_CSRF_ENABLED'] = True
        self.assertEqual(code, 1)
        self.assertIn('FAIL', out)

    def test_missing_settings_is_a_usage_error(self):
        with patch.dict(os.environ, {}, clear=True), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(site_smoke.main([]), 2)

    def test_non_http_base_url_is_refused(self):
        with self.assertRaises(ValueError):
            site_smoke.Smoke('file:///etc/passwd', MARKER)


class SmtpAuth(unittest.TestCase):
    def smoke(self):
        return site_smoke.Smoke('http://127.0.0.1:9', MARKER)

    @patch('site_smoke.smtplib.SMTP')
    def test_login_without_sending(self, mock_smtp):
        server = mock_smtp.return_value.__enter__.return_value
        env = {'EMAIL_HOST_USER': 'u@example.com', 'EMAIL_HOST_PASSWORD': 'hunter2'}
        smoke = self.smoke()
        with patch.dict(os.environ, env), contextlib.redirect_stdout(io.StringIO()) as out:
            smoke.smtp_auth()
        server.starttls.assert_called_once()
        server.login.assert_called_once_with('u@example.com', 'hunter2')
        server.send_message.assert_not_called()
        self.assertEqual(smoke.passed, 1)
        self.assertNotIn('hunter2', out.getvalue())

    @patch('site_smoke.smtplib.SMTP')
    def test_rejected_credentials_fail_without_printing_them(self, mock_smtp):
        import smtplib
        mock_smtp.return_value.__enter__.return_value.login.side_effect = \
            smtplib.SMTPAuthenticationError(535, b'bad hunter2')
        env = {'EMAIL_HOST_USER': 'u@example.com', 'EMAIL_HOST_PASSWORD': 'hunter2'}
        smoke = self.smoke()
        with patch.dict(os.environ, env), contextlib.redirect_stdout(io.StringIO()) as out:
            smoke.smtp_auth()
        self.assertEqual(smoke.passed, 0)
        self.assertIn('SMTPAuthenticationError', out.getvalue())
        self.assertNotIn('hunter2', out.getvalue())

    def test_missing_credentials_fail(self):
        smoke = self.smoke()
        with patch.dict(os.environ, {}, clear=True), contextlib.redirect_stdout(io.StringIO()) as out:
            smoke.smtp_auth()
        self.assertIn('FAIL smtp login', out.getvalue())


if __name__ == '__main__':
    unittest.main()
