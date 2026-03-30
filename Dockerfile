FROM python:3.10-slim

# Cài đặt các gói cần thiết: Chrome & ChromeDriver cho Selenium
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    && wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONIOENCODING=utf-8
ENV PYTHONUNBUFFERED=1

# Cài đặt thư viện Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy mã nguồn dự án
COPY . .

# Gateway mặc định mở cổng 8000
EXPOSE 8000

# Chạy Command mặc định là gateway
CMD ["python", "gateway.py"]
