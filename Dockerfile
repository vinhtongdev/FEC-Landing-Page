# Sử dụng image Python chính thức
FROM python:3.10-slim

# Thiết lập biến môi trường
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Tạo thư mục làm việc
RUN mkdir /app
WORKDIR /app

# Cài các gói cần thiết (cho psycopg2 nếu dùng PostgreSQL)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    python3-dev \
    && apt-get clean

# Sao chép requirements.txt và cài gói
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ code dự án
COPY . /app/

# Thu thập static files (nếu có)
RUN python manage.py collectstatic --noinput

# Chạy entrypoint.sh
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "ITV_FEC_ICustomer.wsgi:application"]