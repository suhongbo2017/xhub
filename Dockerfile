# ==============================
# X HUB - Video Downloader (Multi-stage)
# ==============================
FROM python:3.12-slim AS base

# 安装系统依赖（ffmpeg + yt-dlp）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    wget \
    ca-certificates \
    curl \
    tini \
    && rm -rf /var/lib/apt/lists/*

# 预装最新版 yt-dlp
RUN pip install --no-cache-dir yt-dlp

WORKDIR /app

# 复制 Python 依赖并预安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

EXPOSE $PORT

# 使用 tini 作为 init 进程，正确处理信号
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "server.py"]
