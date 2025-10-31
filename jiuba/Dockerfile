FROM docker.m.daocloud.io/python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements 文件
COPY requirement.txt .

# 安装 Python 依赖（使用国内镜像加速）
RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install -r requirement.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn --timeout 300

# 复制整个项目代码
COPY . .

# 创建必要的目录
RUN mkdir -p staticfiles media logs

# 收集静态文件（关键步骤！）
RUN python manage.py collectstatic --noinput

# 执行数据库迁移
RUN python manage.py migrate

EXPOSE 80

# 启动 Gunicorn
CMD ["python", "-m", "gunicorn", "jiuba.wsgi:application", "--bind", "0.0.0.0:80", "--workers", "2", "--access-logfile", "-"]