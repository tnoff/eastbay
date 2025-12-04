FROM python:3.14-slim-bookworm

RUN mkdir -p /opt/web /var/log/website
COPY templates/ /opt/web/templates
COPY staticfiles /opt/web/staticfiles
COPY startup.sh requirements.txt app.py /opt/web/
RUN chmod +x /opt/web/startup.sh

RUN pip install -r /opt/web/requirements.txt
RUN rm /opt/web/requirements.txt

CMD ["/opt/web/startup.sh"]