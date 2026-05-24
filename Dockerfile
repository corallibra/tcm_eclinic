# TCM EClinic - CLI 工具镜像（数据导入/导出/迁移）
# GUI 在宿主机运行，Docker 仅提供 PostgreSQL 和 CLI 工具

FROM python:3.14-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py", "--help"]
