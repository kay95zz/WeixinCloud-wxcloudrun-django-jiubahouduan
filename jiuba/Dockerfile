# 使用 DaoCloud 的 Python 镜像
FROM docker.m.daocloud.io/python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 跳过时区设置，直接安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    libjpeg-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 先单独复制 requirements 文件
COPY requirements.txt .

# 设置 pip 配置使用国内源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 升级 pip 并安装依赖
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 复制项目代码
COPY . .

# 创建必要的目录
RUN mkdir -p static media

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]