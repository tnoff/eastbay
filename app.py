import os
import logging
import logging.handlers
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, ValidationError
import phonenumbers
from email.mime.text import MIMEText
import smtplib

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.instrumentation.logging.handler import LoggingHandler
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor

# Setup OpenTelemetry
def setup_otel(app):
    trace.set_tracer_provider(TracerProvider())
    span_processor = BatchSpanProcessor(OTLPSpanExporter())
    trace.get_tracer_provider().add_span_processor(span_processor)
    FlaskInstrumentor().instrument_app(app)

    logger_provider = LoggerProvider()
    set_logger_provider(logger_provider)
    log_exporter = OTLPLogExporter()
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
    handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)

# Configuration
class Config:
    # Secret key for CSRF protection
    SECRET_KEY_FILE = 'secret_key'
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', None)

    if SECRET_KEY is None:
        if os.path.exists(SECRET_KEY_FILE):
            with open(SECRET_KEY_FILE, 'r') as f:
                SECRET_KEY = f.read().strip()
        else:
            raise Exception('No secret key found. Set FLASK_SECRET_KEY env var or create secret_key file')

    # Debug mode
    DEBUG = False
    FORCE_DEBUG = os.environ.get('FORCE_DEBUG', False)
    if os.path.exists(SECRET_KEY_FILE) or FORCE_DEBUG:
        DEBUG = True

    # Contact info
    CONTACT_EMAIL = os.environ.get('CONTACT_EMAIL', 'trang@eastbaymassageandlymph.com')
    CONTACT_NUMBER = os.environ.get('CONTACT_NUMBER', '(925) 570-7495')

    # Email settings
    EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'eastbaymassageandlymph@gmail.com')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', None)
    EMAIL_ENABLED = EMAIL_HOST_PASSWORD is not None

    # Phone number settings
    PHONENUMBER_DEFAULT_REGION = 'US'

    # Logging
    LOG_FILE = os.environ.get('LOG_FILE', None)
    if LOG_FILE is None:
        if os.path.exists(SECRET_KEY_FILE):
            LOG_FILE = 'website.log'
        elif os.path.exists('/var/log/website'):
            LOG_FILE = '/var/log/website/website.log'
        else:
            LOG_FILE = 'website.log'  # Fallback to current directory

# Initialize Flask app
app = Flask(__name__, static_folder='staticfiles', static_url_path='/static')
app.config.from_object(Config)

# Setup CSRF protection
csrf = CSRFProtect(app)

# Setup OpenTelemetry
setup_otel(app)

# Setup logging
logging.basicConfig(
    level=logging.DEBUG if app.config['DEBUG'] else logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler(
            app.config['LOG_FILE'],
            maxBytes=1024 * 1024 * 5,  # 5 MB
            backupCount=5
        )
    ]
)

logger = logging.getLogger(__name__)

# Phone number validator
def validate_phone(form, field):
    if field.data:
        try:
            parsed = phonenumbers.parse(field.data, app.config['PHONENUMBER_DEFAULT_REGION'])
            if not phonenumbers.is_valid_number(parsed):
                raise ValidationError('Invalid phone number')
        except phonenumbers.NumberParseException:
            raise ValidationError('Invalid phone number')

# Contact form
class ContactForm(FlaskForm):
    name = StringField('Name', validators=[
        DataRequired(message='Name is required'),
        Length(max=1024)
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Invalid email'),
        Length(max=1024)
    ])
    phone_number = StringField('Phone Number', validators=[
        validate_phone,
        Length(max=20)
    ])
    message = TextAreaField('Message', validators=[
        DataRequired(message='Message is required'),
        Length(max=30 * 1024)
    ])

# Helper function to send email
def send_email(name, email, phone_number, message):
    if not app.config['EMAIL_ENABLED']:
        logger.info(f"DEV MODE: Contact form submitted successfully")
        logger.info(f"  Name: {name}")
        logger.info(f"  Email: {email}")
        logger.info(f"  Phone: {phone_number}")
        logger.info(f"  Message: {message}")
        return

    try:
        msg_body = f'From: {email}\nName: {name}\nPhone Number: {phone_number}\nMessage: {message}'
        msg = MIMEText(msg_body)
        msg['Subject'] = f'Web Form Message {datetime.now()}'
        msg['From'] = app.config['EMAIL_HOST_USER']
        msg['To'] = app.config['CONTACT_EMAIL']

        with smtplib.SMTP(app.config['EMAIL_HOST'], app.config['EMAIL_PORT']) as server:
            server.starttls()
            server.login(app.config['EMAIL_HOST_USER'], app.config['EMAIL_HOST_PASSWORD'])
            server.send_message(msg)

        logger.info(f"Email sent successfully from {email}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise

# Routes
@app.route('/')
def home():
    form = ContactForm()
    return render_template('home.html',
                         form=form,
                         show_contact=False,
                         contact_email=app.config['CONTACT_EMAIL'],
                         contact_number=app.config['CONTACT_NUMBER'],
                         contact_number_no_space=app.config['CONTACT_NUMBER'].replace('-', '').replace('(', '').replace(')', '').replace(' ', ''))

@app.route('/send_message/', methods=['POST'])
def send_message():
    form = ContactForm()

    if form.validate_on_submit():
        try:
            send_email(
                form.name.data,
                form.email.data,
                form.phone_number.data or '',
                form.message.data
            )
            return redirect(url_for('message_successful'))
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            form.errors['_general'] = ['Failed to send message. Please try again.']

    # If validation fails, show form with errors
    return render_template('home.html',
                         form=form,
                         show_contact=True,
                         contact_email=app.config['CONTACT_EMAIL'],
                         contact_number=app.config['CONTACT_NUMBER'],
                         contact_number_no_space=app.config['CONTACT_NUMBER'].replace('-', '').replace('(', '').replace(')', '').replace(' ', ''))

@app.route('/message_successful/')
def message_successful():
    return render_template('message.html',
                         contact_email=app.config['CONTACT_EMAIL'],
                         contact_number=app.config['CONTACT_NUMBER'])

@app.route('/health')
def health():
    return 'OK', 200

# Error handlers
@app.errorhandler(403)
def forbidden(e):
    logger.warning(f"CSRF violation attempt detected. IP: {request.remote_addr}")
    logger.warning(f"Headers: {dict(request.headers)}")
    return "CSRF token missing or invalid.", 403

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=app.config['DEBUG'])
