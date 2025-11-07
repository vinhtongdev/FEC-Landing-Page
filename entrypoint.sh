#!/bin/bash

# Chạy migration
python manage.py migrate

# Tạo superuser (uncomment nếu cần)
# python manage.py createsuperuser --noinput

# Chạy Daphne cho ASGI (hỗ trợ WebSocket)
exec daphne -b 0.0.0.0 -p 8000 ITV_FEC_ICustomer.asgi:application