#!/bin/bash
set -e

while ! nc -z db 5432; do
  sleep 0.1
done

echo "Running migrations"

python manage.py migrate
exit 0
