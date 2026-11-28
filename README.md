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
| `SMOKE_TEST_EMAIL` | no | unset | The sender address the smoke test submits the form with. A submission from exactly this address (case and surrounding spaces ignored) gets the normal success page and **no email is sent**. Every response also carries it in an `X-Smoke-Test-Email` header. Unset turns it off. See [Smoke test](#smoke-test). |
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

## Smoke test

`smoke/site_smoke.py` (standard library only, installed in the image as `site-smoke`) asks a running
site what a visitor would: `/health`, the homepage, a stylesheet, a 404, then the contact form.
It prints `PASS` or `FAIL` per check and exits 0 or 1.

```bash
SMOKE_BASE_URL=https://eastbaymassageandlymph.com SMOKE_TEST_EMAIL=smoke-test@eastbaymassageandlymph.com \
  python3 smoke/site_smoke.py            # add --smtp-auth to also check the mail login
```

**It never emails the owner.** The form is submitted as `SMOKE_TEST_EMAIL`, which the server accepts
without sending, and only **after** the server announces that address in the `X-Smoke-Test-Email`
header. A server that has not deployed `SMOKE_TEST_EMAIL` does not announce it, so the form checks fail
with "NOT submitting the form" and nothing is posted. The checks: submit gets a 302 to
`/message_successful/`, that page renders, a bad email is rejected with an error, and a submission with
no CSRF token is refused.

`--smtp-auth` logs in to the mail server (`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`,
`EMAIL_HOST_PASSWORD`) and quits without sending, to catch a revoked or expired app password. It runs
only where the credentials are present, i.e. in the cluster. `--smtp-only` does just that login and none
of the web checks, so it can run on its own (slower) schedule.

It runs in three places, so a failure says which side of the ingress is broken:

- **In the cluster**: CronJobs and a post-deploy Job in
  [`tnoff/docker-apps`](https://github.com/tnoff/docker-apps/tree/main/apps/eastbaymassage) run it with
  this image against the `website-svc` Service every 15 minutes, and the mail login (`--smtp-only`) after each
  deploy and daily. A pod cannot reach the public URL (ingress-nginx needs PROXY protocol and kube-proxy skips
  the load balancer), so this covers the site but not DNS, TLS or the ingress.
- **From GitHub**: `.github/workflows/smoke-public.yml` runs it every 15 minutes against
  `https://eastbaymassageandlymph.com` and checks the certificate has 14 days left. This walks the
  whole public path, including the form POST through the ingress.

Failures post to `#smoke-tests` in Discord. If the public probe fails and the in-cluster one passes,
look in front of the site (DNS, the load balancer, the ingress, the certificate).

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
