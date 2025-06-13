#!/bin/sh
set -e

python manage.py migrate

make load_data

python manage.py runserver 0.0.0.0:12345