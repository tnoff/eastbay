FROM python:3.13-slim-bookworm

RUN apt-get update && apt-get install -y gcc libpq-dev

RUN mkdir -p /opt/web /var/log/website
COPY eastbay_massage /opt/web/eastbay_massage
COPY templates/ /opt/web/templates
COPY staticfiles /opt/web/staticfiles
COPY startup.sh requirements.txt manage.py /opt/web/
RUN chmod +x /opt/web/startup.sh

RUN pip install -r /opt/web/requirements.txt psycopg2-binary

RUN apt-get remove -y gcc && apt-get autoremove -y
RUN rm /opt/web/requirements.txt

CMD ["/opt/web/startup.sh"]