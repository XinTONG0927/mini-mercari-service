FROM python:3.9-alpine

# 设置环境变量，避免 Python 缓存 `.pyc` 文件
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 设置工作目录
WORKDIR /app

# 安装依赖：pip 和编译环境（如有需要）
RUN apk update && apk add --no-cache \
    build-base \
    libffi-dev \
    musl-dev \
    gcc \
    python3-dev \
    openssl-dev

# 如果有 requirements.txt，则复制并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

EXPOSE 9000

RUN addgroup -S mercari && adduser -S trainee -G mercari
RUN chown -R trainee:mercari /app/python/db

USER trainee

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]

