FROM python:3.11-slim

WORKDIR /app

RUN useradd -m -u 1000 simulator

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY simulator.py .

RUN chown -R simulator:simulator /app

USER simulator

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD ps aux | grep -q "[p]ython.*simulator.py" || exit 1

CMD ["python", "-u", "simulator.py"]
