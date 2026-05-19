# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Зависимости отдельным слоем для кэширования
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Non-root user — обязательно в продакшне
RUN useradd -m -u 1001 agent
USER agent

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]