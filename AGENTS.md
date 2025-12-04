# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository.

## Project Overview

Eastbay Massage and Lymph website - a simple Flask application for a massage therapy business. The site is primarily static HTML with a contact form. The site is designed to run in Docker/Kubernetes on Digital Ocean.

## Development Commands

### Setup
```bash
pip install -r requirements.txt
```

### Run Development Server
```bash
# Development mode (using Flask's built-in server)
python app.py

# Production mode (using gunicorn)
gunicorn --bind 0.0.0.0:8000 --workers 4 app:app
```

The development server runs on http://localhost:8000 by default.

### Run Tests
```bash
# Run all tests
python -m unittest test_app.py

# Run with verbose output
python -m unittest -v test_app.py

# Run specific test class
python -m unittest test_app.FlaskAppTestCase

# Run specific test method
python -m unittest test_app.FlaskAppTestCase.test_home_page_loads
```

### Docker Build
```bash
docker build -t eastbay-massage .
```

The Dockerfile uses Python 3.14-slim-bookworm.

## Architecture

### Application Structure

Simple Flask application with all code in a single `app.py` file:

- **app.py** - Main Flask application containing:
  - Configuration (Config class)
  - OpenTelemetry setup
  - ContactForm (Flask-WTF form)
  - Email sending logic
  - Route handlers (home, send_message, message_successful)
  - Error handlers
- **templates/** - Jinja2 templates (base.html, home.html, message.html)
- **staticfiles/** - Static assets (served by Flask in dev, gunicorn in production)
- **test_app.py** - Unit tests for the application

### Configuration & Environment

**Development vs Production Detection:**
- If `secret_key` file exists locally → Development mode (DEBUG=True)
- Otherwise → Production mode (reads FLASK_SECRET_KEY from environment)

**Key Environment Variables:**
- `FLASK_SECRET_KEY` - Required in production (or use `secret_key` file for dev)
- `FORCE_DEBUG` - Force debug mode even without secret_key file
- `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` - Gmail SMTP credentials for contact form
- `EMAIL_HOST`, `EMAIL_PORT` - SMTP server configuration (defaults to Gmail)
- `CONTACT_EMAIL` - Recipient email (default: trang@eastbaymassageandlymph.com)
- `CONTACT_NUMBER` - Phone number displayed on site

**Email Functionality:**
- Email sending is disabled unless `EMAIL_HOST_PASSWORD` is set
- Uses Gmail SMTP by default
- Contact form data is printed to console when email is disabled
- Sends email via Python's smtplib directly (no framework wrapper needed)

### Key Features

**OpenTelemetry Integration:**
- Configured in `app.py` with OTLP exporters for traces and logs
- Flask is automatically instrumented via FlaskInstrumentor
- Exports to standard OTLP gRPC endpoint

**Static Files:**
- Served from `staticfiles/` directory
- Flask static file serving in development
- Gunicorn serves static files in production
- Bootstrap 5 and Bootstrap Icons loaded via CDN (no package dependencies)

**Logging:**
- Logs to `/var/log/website/website.log` in production
- Logs to `website.log` in project root during development
- Rotating file handler (5MB max, 5 backups)
- CSRF violations logged via Flask error handler

**Form Validation:**
- ContactForm uses Flask-WTF and WTForms
- Phone number validation via `phonenumbers` library directly
- Default region: US
- Email validation via WTForms Email validator
- Max message length: 30KB
- CSRF protection via Flask-WTF

### URL Routes

1. `/` - Home page with contact form (GET)
2. `/send_message/` - Form submission endpoint (POST only)
3. `/message_successful/` - Success confirmation page (GET)

## Deployment

The site is containerized and deploys to Digital Ocean:
- Container startup script: `startup.sh`
- Runs gunicorn with 4 workers
- Serves on port 8000 internally
- Production domain: eastbaymassageandlymph.com

## Testing Philosophy

Tests focus on critical functionality:
- Route accessibility and rendering (FlaskAppTestCase)
- Form validation and submission (FlaskAppTestCase)
- Email sending when enabled (with mocking)
- CSRF protection
- Form field validation (ContactFormTestCase)

Use Python's unittest framework with Flask's test_client for integration testing.
