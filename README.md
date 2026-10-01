# Eastbay Massage Website

Flask application serving [eastbaymassageandlymph.com](https://eastbaymassageandlymph.com)
— mostly static HTML with a server-side contact form that emails inbound
messages to the business owner.

Runs in Docker on OKE. GitHub Actions builds and pushes the image via the
shared workflows in `tnoff/github-workflows`; the SHA pin in
`tnoff/docker-apps` is bumped automatically after each push.

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
| `LOG_FILE` | no | (auto-detected) | Override the log file path; otherwise `website.log` in dev, `/var/log/website/website.log` in prod |

## URL routes

| Method | Path | Behaviour |
|---|---|---|
| GET | `/` | Home page with the contact form |
| POST | `/send_message/` | Submit contact form |
| GET | `/message_successful/` | Submission confirmation |
| GET | `/health` | Liveness/readiness probe target (excluded from tracing) |

## Running

For local dev, build, and tests see [DEVELOPMENT.md](https://github.com/tnoff/eastbay/blob/main/docs/DEVELOPMENT.md).

The production container's entrypoint is `startup.sh`, which runs
`gunicorn --bind 0.0.0.0:8000 --workers 4 app:app`.

## Logging

- Dev: `website.log` in the project root (rotating, 5 MB × 5 backups)
- Prod: `/var/log/website/website.log` (same rotation policy)
- CSRF violations are logged at WARNING via a Flask error handler.

## Deployment

The Kubernetes manifests live in
[`tnoff/docker-apps/apps/eastbaymassage/`](https://github.com/tnoff/docker-apps/tree/main/apps/eastbaymassage).
On each merge to `main` that touches an image input, CI pushes the image
to OCIR with a short-SHA tag and sends a `repository_dispatch`
(`bump_source: eastbay`) to docker-apps, whose `bump-image-pin.yml` opens
the PR that bumps the pinned tag.

The SMTP credentials, contact details and Flask secret key come from the
terraform-managed Secret `eastbay-website-creds` (loaded via `envFrom`); the
Deployment rolls automatically when it rotates.

See [AGENTS.md](https://github.com/tnoff/eastbay/blob/main/docs/AGENTS.md) for non-obvious code internals.
