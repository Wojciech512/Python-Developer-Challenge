#!/bin/bash
set -e

while ! nc -z db 5432; do
  sleep 0.1
done

echo "Runserver starting"

python manage.py runserver --insecure 0.0.0.0:8000
