FROM docker.m.daocloud.io/python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirement
COPY requirement.txt .

# 安装 Python 依赖
RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install -r requirement.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 300

# 安装 gunicorn 使用国内镜像
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ --trusted-host pypi.tuna.tsinghua.edu.cn gunicorn

# 如果有安装requirements.txt的命令，也一并修改：
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ --trusted-host pypi.tuna.tsinghua.edu.cn -r requirements.txt
# 复制项目代码
COPY . .

# 创建必要目录
RUN mkdir -p media static

# 微信云托管使用 80 端口
EXPOSE 80

# 启动命令
CMD ["gunicorn", "jiuba.wsgi:application", "--bind", "0.0.0.0:80", "--workers", "2", "--access-logfile", "-"]