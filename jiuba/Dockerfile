FROM docker.m.daocloud.io/python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# 安装系统依赖（包括MySQL客户端）
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

# 创建静态文件目录（确保存在）- 保留这个重要命令
RUN mkdir -p staticfiles

# 创建媒体文件目录 - 新增这个命令
RUN mkdir -p media

# 执行数据库迁移 - 保留这个重要命令（但注意：在构建时执行迁移可能有问题）
RUN python manage.py migrate

# 强制收集静态文件（添加详细输出）- 保留这个重要命令
RUN echo "开始收集静态文件..." && \
    python manage.py collectstatic --noinput --clear && \
    echo "静态文件收集完成" && \
    ls -la staticfiles/ && \
    echo "管理员静态文件：" && \
    ls -la staticfiles/admin/ || echo "静态文件收集可能有问题"

EXPOSE 80

# 使用启动脚本而不是直接运行命令
CMD ["sh", "-c", "python manage.py migrate && python -m gunicorn jiuba.wsgi:application --bind 0.0.0.0:80 --workers 2"]