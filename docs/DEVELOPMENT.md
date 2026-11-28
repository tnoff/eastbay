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

`test_smoke.py` runs `smoke/site_smoke.py` against the real app on a local port (a healthy app passes,
a server without `SMOKE_TEST_EMAIL` is never posted to, nothing listening fails) and tests `--smtp-auth`
with `smtplib` mocked. It needs `FLASK_SECRET_KEY` set, like the rest.

There is no coverage gate.

## Smoke test

```bash
FLASK_SECRET_KEY=dev python -m unittest test_smoke.py
SMOKE_BASE_URL=http://localhost:8000 SMOKE_TEST_EMAIL=smoke-test@example.com python smoke/site_smoke.py
```

Run the second against a local app started with `SMOKE_TEST_EMAIL=smoke-test@example.com` and
`EMAIL_HOST_PASSWORD` unset. It is standard library only on purpose (it runs from the production image).

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

CI is GitHub Actions, calling reusable workflows from
`tnoff/github-workflows` (pinned by SHA):

- `ci.yml` (PRs): `trufflehog.yml` (secret scan), `pre-commit.yml`
  (bandit), `spellcheck.yml`, `docker-build-check.yml` (image build +
  image secret scan, only when image-input files changed),
  `bump-version.yml` (on `renovate/dev-*` PRs),
  `check-workflow-contracts.yml`. The `CI result` job aggregates them and is
  the one required check.
- `smoke-public.yml` (every 15 minutes): runs `smoke/site_smoke.py` against
  https://eastbaymassageandlymph.com from a GitHub runner, checks the certificate, and posts to
  `#smoke-tests` on failure. See the Smoke test section of [README.md](README.md).
- `release.yml` (push to `main`): `assemble-changelog.yml`, `tag.yml`,
  `docker-push-oidc.yml` (only when image-input files changed; logs in with the job's
  GitHub OIDC identity, no stored OCIR credential), then
  `trigger-bump-dispatch.yml`, which sends a `repository_dispatch` to
  docker-apps to open the image-pin bump PR.
- `scheduled.yml`: `renovate.yml`, `branch-cleanup.yml`
- `notify-failure.yml`: `discord-notify.yml`
- `techdocs-publish.yml`: publishes this site to Backstage TechDocs when
  `docs/**`, `mkdocs.yml` or `catalog-info.yaml` change.

There is no test execution or coverage gate in CI; `test_app.py` only runs
locally (see [Tests](#tests)).

`VERSION` at the repo root is the single source of truth for tagging.
