FROM python:3.13-slim-bookworm

RUN mkdir -p /opt/web /var/log/website
COPY eastbay_massage /opt/web/eastbay_massage
COPY templates/ /opt/web/templates
COPY staticfiles /opt/web/staticfiles
COPY startup.sh requirements.txt manage.py /opt/web/
RUN chmod +x /opt/web/startup.sh

RUN pip install -r /opt/web/requirements.txt

RUN rm /opt/web/requirements.txt

CMD ["/opt/web/startup.sh"]