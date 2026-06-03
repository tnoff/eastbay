# Development

Local dev setup, tests, and Docker build. User-facing description of
the site and its env-var schema live in [README.md](README.md); for
non-obvious code internals see [AGENTS.md](AGENTS.md).

## Prerequisites

- Python 3.14 (matches `Dockerfile`'s `python:3.14-slim-bookworm` base)
- Docker (for the production-image build)

## Setup

```bash
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
```

To run in dev mode without setting `FLASK_SECRET_KEY`, drop a file
named `secret_key` (any content) in the repo root — `app.py` detects
its presence and switches on debug mode.

```bash
echo dev > secret_key
```

## Running locally

Flask dev server (debug mode if `secret_key` file is present):

```bash
python app.py
# → http://localhost:8000
```

Production-equivalent with gunicorn:

```bash
gunicorn --bind 0.0.0.0:8000 --workers 4 app:app
```

To exercise the contact-form email path without spamming a real
inbox, leave `EMAIL_HOST_PASSWORD` unset — `app.py` skips the SMTP
call and logs the form payload to stdout instead.

## Tests

Plain `unittest`:

```bash
python -m unittest test_app.py            # all
python -m unittest -v test_app.py         # verbose
python -m unittest test_app.FlaskAppTestCase
python -m unittest test_app.FlaskAppTestCase.test_home_page_loads
```

`test_app.py` covers:

- Route accessibility / rendering (`FlaskAppTestCase`)
- Form validation + submission, including CSRF
- Email delivery (with `smtplib.SMTP` mocked)
- Per-field validators (`ContactFormTestCase`)

There is no coverage gate.

## Docker build

```bash
docker build -t eastbay-massage .
docker run --rm -p 8000:8000 \
  -e FLASK_SECRET_KEY=dev \
  -e CONTACT_EMAIL=test@example.com \
  -e CONTACT_NUMBER=555-1234 \
  -e EMAIL_HOST_USER=test@example.com \
  eastbay-massage
```

`startup.sh` is the container entrypoint and runs gunicorn with 4
workers on port 8000.

## CI / release

CI is GitLab CI. `.gitlab-ci.yml` pulls templates from
`tnoff-projects/github-workflows`:

- `buildkit-build-check.yml` — MR-time Dockerfile build check
- `buildkit-docker-push.yml` — build + push on default branch
- `trigger-bump.yml` — open an MR in `docker-apps` to bump the SHA pin
- `trufflehog.yml`, `trufflehog-image.yml` — secret scans
- `tag.yml`, `bump-version.yml` — tag from `VERSION` and bump on the
  default branch
- `renovate.yml` — scheduled dependency updates
- `discord-notify.yml` — failure notifications

`VERSION` at the repo root is the single source of truth — bump it,
push, and CI handles tagging + the release.
