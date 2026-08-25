FROM python:3.11-slim

# Install ffmpeg + clean up
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8866

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8866"]
