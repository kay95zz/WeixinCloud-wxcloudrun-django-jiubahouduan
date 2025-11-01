FROM docker.m.daocloud.io/python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements 文件
COPY requirement.txt .

# 安装 Python 依赖
RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install -r requirement.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn --timeout 300

# 复制整个项目代码
COPY . .

# 创建必要的目录
RUN mkdir -p staticfiles media

# 只生成迁移文件，不执行迁移（因为构建时可能没有数据库连接）
RUN echo "生成迁移文件..." && \
    python manage.py makemigrations --noinput || echo "迁移文件生成完成或已有迁移文件"

# 收集静态文件
RUN echo "开始收集静态文件..." && \
    python manage.py collectstatic --noinput --clear && \
    echo "静态文件收集完成"

EXPOSE 80

# 在启动时执行实际迁移（确保有数据库连接）
CMD ["sh", "-c", "echo '开始数据库迁移...' && python manage.py migrate && echo '迁移完成，启动服务...' && python -m gunicorn jiuba.wsgi:application --bind 0.0.0.0:80 --workers 2"]