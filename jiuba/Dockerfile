FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 更换APT源为阿里云
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list

# 安装系统证书包和必要的编译工具
RUN apt-get update && apt-get install -y \
    ca-certificates \
    gcc \
    python3-dev \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && update-ca-certificates --fresh \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 复制 requirements 文件并安装依赖
COPY requirement.txt .
RUN pip install --upgrade pip && \
    pip install -r requirement.txt --timeout 300

# 复制项目代码
COPY . .

# 创建目录
RUN mkdir -p staticfiles media

# 设置环境变量以解决 SSL 问题
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

EXPOSE 80

# 启动命令
CMD ["sh", "-c", "python manage.py collectstatic --noinput && python manage.py migrate && gunicorn jiuba.wsgi:application --bind 0.0.0.0:80 --workers 2 --access-logfile -"]