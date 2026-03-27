FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Create data/log dirs
RUN mkdir -p /app/data /app/logs /app/strategies

ENV PYTHONUNBUFFERED=1
ENV TZ=America/New_York

CMD ["python", "agent.py"]
