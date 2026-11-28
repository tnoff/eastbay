#!/usr/bin/env python3
"""Smoke test of the running site: asks it what a visitor would and exits 0 if every check passes,
1 if any fails. One line per check (PASS or FAIL), then "N/M checks passed".

Standard library only, so it runs from the production image (python, no pip needed) in the in-cluster
smoke CronJob and Job in tnoff/docker-apps (against the Service, which skips DNS, TLS and the
ingress) and from .github/workflows/smoke-public.yml on a GitHub runner (against the public url,
which walks all of it). Same file in both, so the two cannot drift apart.

    SMOKE_BASE_URL    no trailing slash, e.g. https://eastbaymassageandlymph.com
    SMOKE_TEST_EMAIL  the sender address the server will not send email for (app.py SMOKE_TEST_EMAIL)
    SMOKE_TRIES       attempts per request that gets no response (default 3)
    SMOKE_TIMEOUT     seconds per attempt (default 15)

    --smtp-auth       also log in to the mail server (EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER,
                      EMAIL_HOST_PASSWORD from the environment) and quit WITHOUT sending anything,
                      to catch a revoked or expired app password. Only runs where those are set.
    --smtp-only       just that login, none of the web checks (needs no SMOKE_BASE_URL). For a
                      slower schedule than the web checks: every 15 minutes is a lot of logins.

THE CONTACT FORM IS SUBMITTED ONLY AFTER THE SERVER HAS SAID IT WILL NOT SEND EMAIL FOR THE SMOKE
ADDRESS (the X-Smoke-Test-Email response header). Without that, the submission would be a real
enquiry in the owner's inbox every 15 minutes. If the header is missing the form checks FAIL and
nothing is posted.

Redirects are not followed: behind the ingress a redirect can name the public host, which a pod
cannot reach.
"""
import argparse
import http.cookiejar
import os
import re
import smtplib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

SMOKE_HEADER = 'X-Smoke-Test-Email'
TITLE = 'East Bay Massage and Lymph Drainage'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Hand a 3xx back to the caller instead of following it"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Smoke:
    def __init__(self, base_url, smoke_email, tries=3, timeout=15):
        # base_url is None only for --smtp-only, which makes no web requests
        if base_url is not None:
            parsed = urllib.parse.urlparse(base_url)
            if parsed.scheme not in ('http', 'https') or not parsed.netloc:
                raise ValueError(f'SMOKE_BASE_URL must be an http(s) url, got {base_url!r}')
        self.base = (base_url or '').rstrip('/')
        self.smoke_email = smoke_email
        self.tries = tries
        self.timeout = timeout
        self.passed = 0
        self.total = 0
        self.cookies = http.cookiejar.CookieJar()
        self.opener = self._opener(self.cookies)

    @staticmethod
    def _opener(jar):
        return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar), NoRedirect)

    def ok(self, message):
        self.passed += 1
        self.total += 1
        print(f'PASS {message}')

    def bad(self, message):
        self.total += 1
        print(f'FAIL {message}')

    def fetch(self, path, data=None, opener=None):
        """(status, headers, body) of the final response, or (None, {}, '') if nothing answered.

        Any status is an answer and is not retried; no response (refused, reset, timed out) is."""
        url = self.base + path
        body = urllib.parse.urlencode(data).encode() if data is not None else None
        for attempt in range(self.tries):
            request = urllib.request.Request(url, data=body)  # nosec B310 - scheme checked in __init__
            try:
                with (opener or self.opener).open(request, timeout=self.timeout) as response:  # nosec B310
                    return response.status, response.headers, response.read().decode('utf-8', 'replace')
            except urllib.error.HTTPError as error:
                return error.code, error.headers, error.read().decode('utf-8', 'replace')
            except (urllib.error.URLError, OSError):
                if attempt + 1 < self.tries:
                    time.sleep(1)
        return None, {}, ''

    def check(self, name, path, status, contains=None):
        got, _headers, body = self.fetch(path)
        if got != status:
            self.bad(f'{name}: status {got if got is not None else "none (no response)"} for {path}, expected {status}')
        elif contains and contains not in body:
            self.bad(f'{name}: {path} answered {status} without {contains!r}')
        else:
            self.ok(f'{name}: {status} for {path}')
        return body if got == status else ''

    def run(self):
        self.check('health', '/health', 200, 'OK')
        home = self.check('homepage', '/', 200, TITLE)

        stylesheet = re.search(r'href="(/static/[^"]+\.css)"', home)
        if stylesheet:
            self.check('stylesheet', stylesheet.group(1), 200)
        else:
            self.bad('stylesheet: no /static/*.css link on the homepage')

        self.check('missing page', '/smoke-no-such-page', 404)
        self.form_checks()

    def form_checks(self):
        status, headers, body = self.fetch('/')
        token = self.csrf_token(body)
        if status != 200 or not token:
            for name in ('smoke address announced', 'form: submit', 'form: success page',
                         'form: invalid email', 'form: missing token'):
                self.bad(f'{name}: needs the homepage and its CSRF token, which it did not give')
            return

        # The guard: never post unless this server says it will not send email for our address.
        announced = (headers.get(SMOKE_HEADER) or '').strip().lower()
        if announced != self.smoke_email:
            self.bad(f'smoke address announced: {SMOKE_HEADER} is {announced or "missing"}, expected '
                     f'{self.smoke_email}; NOT submitting the form, a submission could send real email')
            for name in ('form: submit', 'form: success page', 'form: invalid email', 'form: missing token'):
                self.bad(f'{name}: skipped, the server did not announce the smoke address')
            return
        self.ok(f'smoke address announced: {SMOKE_HEADER} matches')

        form = {'csrf_token': token, 'name': 'Smoke Test', 'email': self.smoke_email,
                'phone_number': '', 'message': 'Smoke test, not a real enquiry. No email is sent.'}

        status, headers, _body = self.fetch('/send_message/', data=form)
        location = urllib.parse.urlparse(headers.get('Location') or '').path
        if status == 302 and location == '/message_successful/':
            self.ok('form: submit: 302 to /message_successful/')
        else:
            self.bad(f'form: submit: status {status}, Location {location or "none"}, expected 302 to /message_successful/')
        self.check('form: success page', '/message_successful/', 200, 'Message Successfully Sent')

        # Validation still runs: a bad address is re-rendered with the error, not accepted.
        status, _headers, body = self.fetch('/send_message/', data={**form, 'email': 'not-an-email'})
        if status == 200 and 'Invalid email' in body:
            self.ok('form: invalid email: rejected with an error')
        else:
            self.bad(f'form: invalid email: status {status}, expected 200 with "Invalid email"')

        # CSRF protection still on: the same valid form with no session and no token is refused.
        stranger = self._opener(http.cookiejar.CookieJar())
        no_token = {key: value for key, value in form.items() if key != 'csrf_token'}
        status, _headers, _body = self.fetch('/send_message/', data=no_token, opener=stranger)
        # Flask-WTF answers a missing token with 400; 403 is the app's own handler. Either is a refusal.
        if status in (400, 403):
            self.ok(f'form: missing token: refused with {status}')
        else:
            self.bad(f'form: missing token: status {status}, expected 400 or 403')

    @staticmethod
    def csrf_token(html):
        for tag in re.findall(r'<input[^>]*>', html):
            if 'name="csrf_token"' in tag:
                value = re.search(r'value="([^"]+)"', tag)
                return value.group(1) if value else None
        return None

    def smtp_auth(self):
        """Log in to the mail server and quit. Sends nothing. Prints the error class, never the password."""
        host = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
        port = int(os.environ.get('EMAIL_PORT', '587'))
        user = os.environ.get('EMAIL_HOST_USER')
        password = os.environ.get('EMAIL_HOST_PASSWORD')
        if not user or not password:
            self.bad('smtp login: EMAIL_HOST_USER and EMAIL_HOST_PASSWORD are not set here')
            return
        try:
            with smtplib.SMTP(host, port, timeout=self.timeout) as server:
                server.starttls()
                server.login(user, password)
            self.ok(f'smtp login: {host}:{port} accepted the credentials, nothing sent')
        except (smtplib.SMTPException, OSError) as error:
            self.bad(f'smtp login: {host}:{port} {type(error).__name__}')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n', maxsplit=1)[0])
    parser.add_argument('--smtp-auth', action='store_true',
                        help='also log in to the mail server (sends nothing)')
    parser.add_argument('--smtp-only', action='store_true',
                        help='only log in to the mail server (sends nothing), no web checks')
    args = parser.parse_args(argv)

    timeout = int(os.environ.get('SMOKE_TIMEOUT', '15'))
    if args.smtp_only:
        smoke = Smoke(None, '', timeout=timeout)
        smoke.smtp_auth()
    else:
        base = os.environ.get('SMOKE_BASE_URL')
        smoke_email = (os.environ.get('SMOKE_TEST_EMAIL') or '').strip().lower()
        if not base or not smoke_email:
            print('SMOKE_BASE_URL and SMOKE_TEST_EMAIL must be set', file=sys.stderr)
            return 2
        smoke = Smoke(base, smoke_email, tries=int(os.environ.get('SMOKE_TRIES', '3')), timeout=timeout)
        smoke.run()
        if args.smtp_auth:
            smoke.smtp_auth()
    print(f'{smoke.passed}/{smoke.total} checks passed')
    return 0 if smoke.passed == smoke.total else 1


if __name__ == '__main__':
    sys.exit(main())
