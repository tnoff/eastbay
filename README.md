# Eastbay Massage Website

Eastbay Massage and lymph website.

Simple Flask application, mostly static HTML with a contact form.

## Install requirements

Pip install the requirements

```
$ pip install -r requirements.txt
```

## Run the server

Development mode:
```
$ python app.py
```

Production mode (with gunicorn):
```
$ gunicorn --bind 0.0.0.0:8000 --workers 4 app:app
```

## Docker build

Install docker and run, site ideally runs via docker or k8s.

By default builds image and pushes to the digital ocean repo.