FROM python:3.13-alpine

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py feeds.json ./

ENV PORT=8080 \
    CONFIG_PATH=/app/feeds.json \
    PYTHONUNBUFFERED=1

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:8080/health || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "4", "--timeout", "60", "app:app"]
