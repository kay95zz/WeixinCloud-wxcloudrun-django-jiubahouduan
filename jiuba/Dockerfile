FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# 更新 APT 源为国内镜像（正确的路径）
RUN echo "deb https://mirrors.aliyun.com/debian/ bookworm main non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb https://mirrors.aliyun.com/debian/ bookworm-updates main non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.aliyun.com/debian/ bookworm-backports main non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.aliyun.com/debian-security bookworm-security main non-free non-free-firmware" >> /etc/apt/sources.list

# 安装最小系统依赖
RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements 文件
COPY requirement.txt .

# 使用国内 PyPI 镜像安装 Python 依赖
RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install -r requirement.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 300

# 复制项目代码
COPY . .

# 创建必要目录
RUN mkdir -p staticfiles media

EXPOSE 80

# 启动命令
CMD ["gunicorn", "jiuba.wsgi:application", "--bind", "0.0.0.0:80", "--workers", "2"]