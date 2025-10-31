FROM docker.m.daocloud.io/python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# 复制 requirements 文件
COPY requirement.txt .

# 安装 Python 依赖
RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install -r requirement.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn --timeout 300

# 复制整个项目代码
COPY . .

# 创建静态文件目录（确保存在）
RUN mkdir -p staticfiles

# 执行数据库迁移
RUN python manage.py migrate

# 强制收集静态文件（添加详细输出）
RUN echo "开始收集静态文件..." && \
    python manage.py collectstatic --noinput --clear && \
    echo "静态文件收集完成" && \
    ls -la staticfiles/ && \
    echo "管理员静态文件：" && \
    ls -la staticfiles/admin/ || echo "静态文件收集可能有问题"

EXPOSE 80

CMD ["python", "-m", "gunicorn", "jiuba.wsgi:application", "--bind", "0.0.0.0:80", "--workers", "2"]