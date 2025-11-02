FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 安装完整的证书和网络工具
RUN apt-get update && apt-get install -y \
    ca-certificates \
    openssl \
    curl \
    && update-ca-certificates --fresh \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 设置证书环境变量
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# 复制 requirements 文件
COPY requirement.txt .

# 安装 Python 依赖
RUN pip install --upgrade pip && \
    pip install -r requirement.txt

# 复制项目代码
COPY . .

# 创建必要目录
RUN mkdir -p staticfiles media

EXPOSE 80

# 启动命令
CMD ["gunicorn", "jiuba.wsgi:application", "--bind", "0.0.0.0:80", "--workers", "2"]