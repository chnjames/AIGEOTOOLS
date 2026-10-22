FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/uploads /app/data /app/knowledge_base

# 创建非 root 用户运行应用
RUN useradd -r -u 1000 -g appgroup appuser && \
    chown -R appuser:appgroup /app
USER appuser

ENV PYTHONPATH=/app
ENV DATABASE_URL=sqlite+aiosqlite:////app/data/geo_app.db
ENV UPLOAD_DIR=/app/uploads
ENV KNOWLEDGE_DIR=/app/knowledge_base

# 数据持久化卷
VOLUME ["/app/data", "/app/uploads", "/app/knowledge_base"]

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
