# AGENTS.md

Guidance for AI coding agents working in this repository. For an
overview of the site, env-var schema, and routes see [README.md](README.md);
for local setup, tests, and Docker build see [DEVELOPMENT.md](DEVELOPMENT.md).

## What this is

Single-file Flask app (`app.py`) with a Jinja2 template directory and
a static-files directory. Everything — config loading, OpenTelemetry
setup, the contact form, email delivery, route handlers, error
handlers — lives in `app.py`. There is no application factory and no
blueprint structure; if you need to add a route, add it to `app.py`.

```
.
├── app.py             # Everything
├── templates/         # base.html, home.html, message.html
├── staticfiles/       # CSS, JS, images
├── test_app.py        # unittest tests
├── startup.sh         # Container entrypoint (runs gunicorn)
├── Dockerfile         # python:3.14-slim-bookworm
├── docker-compose.yml # Local dev convenience
├── requirements.txt
└── VERSION            # source of truth for release tagging
```

## Non-obvious internals

### Dev vs prod is detected by the `secret_key` *file*

`app.py` checks for a file named `secret_key` in the working directory
on startup. If present, the app runs in **debug mode** and uses the
file contents as the Flask secret key. If absent, the app reads
`FLASK_SECRET_KEY` from the environment. `FORCE_DEBUG=1` overrides to
debug mode regardless.

This dual mechanism exists because containers in dev sometimes have
the file mounted but no env var; prod has the env var but no file. If
you change the detection logic, both paths need to keep working.

### Email is opt-in via `EMAIL_HOST_PASSWORD`

The contact form submission code calls `smtplib.SMTP` **only if**
`EMAIL_HOST_PASSWORD` is set. With it unset (the default in dev), the
form payload is logged to stdout and the user still sees the success
page. This is intentional — it keeps local dev from spamming a real
inbox.

If you ever consolidate the `if EMAIL_HOST_PASSWORD` guard, preserve
the "log and succeed" behaviour for the unset case. Failing the
submission silently when the operator forgot to set a password would
be a worse UX than continuing.

### OTel is unconditional

`setup_otel(app)` runs at import time and registers OTLP exporters
unconditionally. Without an OTLP collector reachable at the SDK's
default endpoint, exports fail but the app still works. In local dev
this generates warning logs; if you want them silent, set
`OTEL_SDK_DISABLED=true`. Don't add an in-code gate to disable OTel
based on env — the SDK already has one.

### `phonenumbers` validation, not WTForms

Phone numbers are validated by calling `phonenumbers.parse(..., 'US')`
directly inside a custom WTForms validator, not via a third-party
WTForms-phonenumbers extension. Region defaults to `US`. If we need
to accept international numbers, lift the region default — don't
add another library.

### Static files served by Flask in both modes

Even in production (gunicorn), static files are served by Flask, not
by a fronting nginx. This works because the container sits behind
ingress-nginx in the cluster and the request volume is low. If
traffic ever matters, the right fix is to add a `Cache-Control` header
on `/static/`, not to add a nginx sidecar.

### Logs go to file, not just stdout

Both dev and prod use a `RotatingFileHandler`:

- Dev: `website.log` in the project root
- Prod: `/var/log/website/website.log`

Rotation is 5 MB × 5 backups. The Dockerfile creates `/var/log/website`;
the K8s manifest in `docker-apps` mounts a writable volume there.
Don't switch to stdout-only without also stripping the file handler.

## Conventions

- New routes go in `app.py` next to the existing handlers, not in a
  separate module.
- New env vars get a default in `Config` and a row in
  [README.md](README.md#configuration).
- New tests go in `test_app.py` mirroring the existing
  `FlaskAppTestCase` / `ContactFormTestCase` split.
