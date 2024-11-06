FROM ubuntu:24.04

RUN apt-get update && apt-get -y upgrade
RUN apt-get install -y python3-dev python3-virtualenv libpq-dev

RUN mkdir -p /opt/web /var/log/website
COPY eastbay_massage /opt/web/eastbay_massage
COPY templates/ /opt/web/templates
COPY staticfiles /opt/web/staticfiles
COPY startup.sh requirements.txt manage.py /opt/web/
RUN chmod +x /opt/web/startup.sh

RUN virtualenv /opt/website-venv
RUN /opt/website-venv/bin/pip install -r /opt/web/requirements.txt  psycopg2-binary

CMD ["/opt/web/startup.sh"]