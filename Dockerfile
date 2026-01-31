FROM python:3.14-slim-bookworm

# Update to latest for security fixes
RUN apt-get update && \
    apt-get upgrade -y --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/web /var/log/website
COPY templates/ /opt/web/templates
COPY staticfiles /opt/web/staticfiles
COPY startup.sh requirements.txt app.py /opt/web/
RUN chmod +x /opt/web/startup.sh

RUN pip install -r /opt/web/requirements.txt
RUN rm /opt/web/requirements.txt

# Create non-root user and set ownership
RUN useradd -r -u 1000 -m -s /bin/bash appuser && \
    chown -R appuser:appuser /opt/web /var/log/website

USER appuser

CMD ["/opt/web/startup.sh"]