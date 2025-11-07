# Sử dụng image Python chính thức
# Upgrade from 3.10 to 3.12 to support autobahn 25.x
FROM python:3.12-slim

# Thiết lập biến môi trường
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Tạo thư mục làm việc
RUN mkdir /app
WORKDIR /app

# Cài các gói cần thiết (mở rộng cho psycopg2, rdkit, pyscf, qutip, v.v.)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    python3-dev \
    libblas-dev \
    liblapack-dev \
    libboost-python1.83-dev \
    libboost-serialization1.83-dev \
    libcairo2-dev \
    libfreetype6-dev \
    libpng-dev \
    pkg-config \
    cmake \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Sao chép requirements.txt và cài gói
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ code dự án
COPY . /app/

# Thu thập static files (nếu có)
RUN python manage.py collectstatic --noinput

# Chạy Daphne cho ASGI (hỗ trợ WebSocket)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "ITV_FEC_ICustomer.asgi:application"]