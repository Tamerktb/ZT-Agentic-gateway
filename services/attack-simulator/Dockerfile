FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir httpx==0.25.2

COPY . .

CMD ["python", "attack_simulator.py"]
