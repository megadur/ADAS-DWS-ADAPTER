FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt pyproject.toml README.md ./
COPY src/ ./src/
COPY samples/ ./samples/

RUN pip install --no-cache-dir -e .

CMD ["python", "-m", "pharmacy_bridge.simulator", "--mqtt-host", "localhost", "--mqtt-port", "1883"]
