FROM docker.m.daocloud.io/python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# 复制 requirements 文件
COPY requirement.txt .

# 安装 Python 依赖
RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install -r requirement.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 300

# 复制项目代码
COPY . .

# 创建目录
RUN mkdir -p staticfiles media

EXPOSE 80

# 启动命令
CMD ["sh", "-c", "python manage.py collectstatic --noinput && python manage.py migrate && python -m gunicorn jiuba.wsgi:application --bind 0.0.0.0:80 --workers 2"]