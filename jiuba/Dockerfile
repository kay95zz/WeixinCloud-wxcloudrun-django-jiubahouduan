# Dockerfile
# 使用一个轻量的Python官方镜像作为基础
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置Python环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 1. 安装系统依赖（这是构建 mysqlclient 等包的关键！）
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 2. 复制依赖文件
COPY requirement.txt /app/

# 3. 安装Python依赖（使用国内镜像加速）
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirement.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --trusted-host pypi.tuna.tsinghua.edu.cn

# 4. 复制项目所有文件到容器
COPY . /app/

# 5. 收集静态文件（Django项目需要）
RUN python manage.py collectstatic --noinput

# 6. 使用 gunicorn 启动Django应用
CMD ["gunicorn", "jiuba.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]