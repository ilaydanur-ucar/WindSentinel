FROM python:3.11-slim

WORKDIR /app

RUN useradd -m -u 1000 consumer

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY consumer.py .
COPY data_sources/ ./data_sources/

RUN chown -R consumer:consumer /app

USER consumer

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD ps aux | grep -q "[p]ython.*consumer.py" || exit 1

CMD ["python", "-u", "consumer.py"]
