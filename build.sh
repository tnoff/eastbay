#!/usr/bin/env bash
set -o errexit

mkdir -p /var/log/website
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate

# DEBUG for static files
echo "Listing static files"
find static/