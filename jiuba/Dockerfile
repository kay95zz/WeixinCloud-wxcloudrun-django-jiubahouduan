FROM docker.m.daocloud.io/python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# 更换为国内APT源，加速系统包安装
RUN sed -i 's/deb.debian.org/debian.cnpmcdn.org/g' /etc/apt/sources.list && \
    sed -i 's/security.debian.org/debian.cnpmcdn.org/g' /etc/apt/sources.list

# 安装系统依赖（使用国内源）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements 文件
COPY requirement.txt .

# 安装 Python 依赖（使用国内源）
RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install -r requirement.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn --timeout 300

# 复制整个项目代码
COPY . .

# 创建必要的目录
RUN mkdir -p staticfiles media

# 只检查迁移，不执行（避免构建时数据库连接问题）
RUN echo "检查迁移状态..." && \
    python manage.py makemigrations --check --dry-run || echo "迁移检查完成"

# 收集静态文件
RUN echo "开始收集静态文件..." && \
    python manage.py collectstatic --noinput --clear && \
    echo "静态文件收集完成"

EXPOSE 80

# 在启动时执行迁移和启动服务
CMD ["sh", "-c", "python manage.py migrate && python -m gunicorn jiuba.wsgi:application --bind 0.0.0.0:80 --workers 2"]