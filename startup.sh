#!/usr/bin/env bash
set -o errexit

cd /opt/web
gunicorn --bind 0.0.0.0:8000 --workers 4 app:app