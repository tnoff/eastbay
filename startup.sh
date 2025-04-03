#!/usr/bin/env bash
set -o errexit

if [ -v ONEBOX_DEPLOY ]; then
    python /opt/web/manage.py migrate
fi

python /opt/web/manage.py runserver 0.0.0.0:8000