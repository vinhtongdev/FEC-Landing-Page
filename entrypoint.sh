#!/bin/bash

# Chạy migration
python manage.py migrate

# Tạo superuser 
# python manage.py createsuperuser --noinput

# Chạy gunicorn
exec gunicorn --bind 0.0.0.0:8000 ITV_FEC_ICustomer.wsgi:application