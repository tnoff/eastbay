#!/usr/bin/env bash
set -o errexit

if [ -v ONEBOX_DEPLOY ]; then
    /opt/website-venv/bin/python /opt/web/manage.py migrate
fi
/opt/website-venv/bin/python /opt/web/manage.py runserver 0.0.0.0:8000