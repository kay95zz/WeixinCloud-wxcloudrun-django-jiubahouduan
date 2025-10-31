FROM docker.m.daocloud.io/python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 先更新软件包列表，再安装依赖（slim 镜像需要先创建 sources.list）
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements 文件
COPY requirement.txt .

# 安装 Python 依赖
RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install -r requirement.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn --timeout 300

# 复制整个项目代码
COPY . .

# 创建必要目录
RUN mkdir -p media static

# 微信云托管使用 80 端口
EXPOSE 80

# 启动命令
CMD ["gunicorn", "jiuba.wsgi:application", "--bind", "0.0.0.0:80", "--workers", "2", "--access-logfile", "-"]