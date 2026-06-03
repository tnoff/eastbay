# Eastbay Massage Website

Flask application serving [eastbaymassageandlymph.com](https://eastbaymassageandlymph.com)
— mostly static HTML with a server-side contact form that emails inbound
messages to the business owner.

Runs in Docker on OKE. CI builds and pushes the image via the shared
templates in `tnoff-projects/github-workflows`; the SHA pin in
`tnoff-projects/docker-apps` is bumped automatically after each push.

## Site features

- Static landing + services pages rendered server-side with Jinja2
- Contact form with CSRF protection, phone-number validation
  (`phonenumbers`), email validation (WTForms)
- Configurable max message length (30 KB)
- Optional SMTP delivery to a configured recipient (defaults to Gmail
  SMTP)
- OpenTelemetry instrumentation (traces + logs) exporting to the
  cluster's OTLP collector

## Configuration

The app reads everything from environment variables.

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `FLASK_SECRET_KEY` | yes (prod) | — | Flask session signing key. In dev, a file named `secret_key` in the repo root substitutes for this. |
| `FORCE_DEBUG` | no | unset | Force Flask debug mode even if `secret_key` is unset / missing |
| `CONTACT_EMAIL` | yes | — | Recipient address for contact form submissions |
| `CONTACT_NUMBER` | yes | — | Phone number displayed on the site |
| `EMAIL_HOST_USER` | yes | — | SMTP login username (also used as the From: address) |
| `EMAIL_HOST_PASSWORD` | no | unset | SMTP password. **Email sending is disabled if unset** — form data is logged to stdout instead. |
| `EMAIL_HOST` | no | Gmail SMTP | SMTP server hostname |
| `EMAIL_PORT` | no | Gmail SMTP | SMTP server port |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | no | (sdk default) | OTel collector endpoint. The deployment manifest in `docker-apps` sets this to the in-cluster collector. |

## URL routes

| Method | Path | Behaviour |
|---|---|---|
| GET | `/` | Home page with the contact form |
| POST | `/send_message/` | Submit contact form |
| GET | `/message_successful/` | Submission confirmation |

## Running

For local dev, build, and tests see [DEVELOPMENT.md](DEVELOPMENT.md).

The production container's entrypoint is `startup.sh`, which runs
`gunicorn --bind 0.0.0.0:8000 --workers 4 app:app`.

## Logging

- Dev: `website.log` in the project root (rotating, 5 MB × 5 backups)
- Prod: `/var/log/website/website.log` (same rotation policy)
- CSRF violations are logged at WARNING via a Flask error handler.

## Deployment

The Kubernetes manifest lives in
[`tnoff-projects/docker-apps/apps/eastbaymassage/`](https://gitlab.com/tnoff-projects/docker-apps/-/tree/main/apps/eastbaymassage).
CI in this repo builds the image, pushes to OCIR with a `:<short-sha>`
tag, and triggers a downstream pipeline that opens an MR in
`docker-apps` to bump the pinned SHA.

See [AGENTS.md](AGENTS.md) for non-obvious code internals.
