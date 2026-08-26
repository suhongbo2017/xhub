# X-HUB — Deployment Guide v1.2.0

This document describes how to deploy **X-HUB** (X/Twitter Video Downloader) on various platforms.  
Version: **1.2.0** | Last updated: 2026-08-26

---

## Quick Links

| Resource | URL |
|----------|-----|
| Source Code | `https://github.com/suhongbo2017/xhub.git` |
| Live Demo | *(add your domain)* |

---

## Prerequisites

| Requirement | Minimum Version | Purpose |
|-------------|----------------|---------|
| Python | 3.9+ | Runtime |
| ffmpeg | Any | Merge HLS (m3u8) videos into MP4 |
| yt-dlp | Latest | Video extraction from X/Twitter |
| Memory | ≥512 MB | Runtime + temp files |

---

## Method A: Direct Python (Ubuntu / Linux VPS)

### 1. Install dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv ffmpeg curl wget
```

### 2. Clone & setup

```bash
cd /opt
git clone https://github.com/suhongbo2017/xhub.git
cd xhub
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Add Twitter Cookie

Export your Twitter cookies from browser DevTools → Application → Cookies → `xcookies.txt`.  
Place it in `/opt/xhub/xcookies.txt`.

> ⚠️ **Cookies expire periodically.** Re-export when parsing fails.

### 4. Start the server

```bash
uvicorn server:app --host 0.0.0.0 --port 8866
```

Or use systemd for auto-start:

```bash
cp xhub.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now xhub.service
sudo systemctl status xhub.service
```

### 5. Nginx reverse proxy (optional but recommended)

```nginx
server {
    listen 443 ssl;
    server_name x.yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/x.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/x.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8866;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Restart: `sudo systemctl restart nginx`

---

## Method B: Docker (Recommended for Production)

### Build & run

```bash
cd /opt/xhub
docker compose up -d --build
```

### docker-compose.yml

```yaml
services:
  xhub:
    build: .
    container_name: xhub
    ports:
      - "8866:8866"
    volumes:
      - ./xcookies.txt:/app/xcookies.txt
      - ./cookies:/app/cookies
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:8866/"]
      interval: 30s
      timeout: 10s
      start_period: 15s
      retries: 3
```

### Volume Mapping Summary

| Container Path | Host Path | Mode | Description |
|----------------|-----------|------|-------------|
| `/app/xcookies.txt` | `./xcookies.txt` | rw | Twitter auth cookies |
| `/app/cookies` | `./cookies` | rw | Additional cookie storage |
| `/app/logs` | `./logs` | rw | Server log output |
| `/app/history.db` | *(auto-created)* | rw | SQLite history database |

---

## Method C: Render.com (Free Tier)

1. Push code to GitHub repo `suhongbo2017/xhub`
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your repo
4. Settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
5. Deploy

Add `xcookies.txt` via Environment Variable or mount as secret.

> ⚠️ Render's free tier spins down after 15 min of inactivity, so first request will have a cold start delay (~30s).

---

## Method D: Railway.app

Same as Render — push to GitHub, connect via Railway, set start command:

```
uvicorn server:app --host 0.0.0.0 --port $PORT
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/parse` | Parse X video URL → return metadata |
| `GET`  | `/api/download?video_url=...&title=...` | Proxy download or merge HLS |
| `GET`  | `/api/history` | View all saved URL records |
| `DELETE` | `/api/db/clear` | Clear all history records |
| `GET`  | `/api/error-log` | View last 200 server errors |
| `GET`  | `/health` | Health check |
| `GET`  | `/api/version` | Returns current version info |

### Parse Request Example

```bash
curl -X POST http://localhost:8866/api/parse \
  -H "Content-Type: application/json" \
  -d '{"url":"https://x.com/user/status/123456"}'
```

Response:
```json
{
  "success": true,
  "data": {
    "title": "Video Title",
    "thumbnail": "https://...",
    "duration": 42,
    "quality": "1280x720",
    "is_m3u8": false,
    "url": "https://cdn.x.com/video.mp4"
  }
}
```

### History API Response

```bash
curl http://localhost:8866/api/history
```

```json
[
  {
    "id": 10,
    "url": "https://x.com/user/status/abc/video/1",
    "timestamp": "2026-08-26T14:30:00",
    "status": "ok",
    "title": "Weather Monitor - Today...",
    "duration": 42,
    "quality": "MP4",
    "is_m3u8": false,
    "source_url": "https://video.twimg.com/amplify_video/..."
  }
]
```

Records are sorted newest-first (`ORDER BY id DESC`). Each record tracks both parse events and download results.

---

## File Structure

```
xhub/
├── server.py              # FastAPI backend (core)
├── history_db.py          # SQLite history storage module
├── index.html             # PWA frontend (retro UI)
├── manifest.json          # PWA manifest
├── sw.js                  # Service Worker
├── requirements.txt       # Python deps
├── version.txt            # Current version: 1.2.0
├── .gitignore             # Git ignore rules
├── Dockerfile             # Docker build config
├── docker-compose.yml     # Docker Compose config
├── tests/                 # pytest integration tests
│   └── test_url_history.py
├── DEPLOY.md              # This file
├── README.md              # Project overview
├── xhub.service           # Systemd unit file
├── start.sh               # Bash startup script
├── render.yaml            # Render.com config
├── cookies/               # Cookie directory (optional)
└── logs/                  # Runtime log output
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| 解析失败 / Parsing failed | Refresh `xcookies.txt` — cookies expire |
| Browser doesn't show new UI | Clear SW cache: DevTools → Application → Service Workers → Unregister |
| HLS 视频无法合并 | `ffmpeg` not installed — `apt install ffmpeg` |
| Port 8866 被占用 | Change port in `uvicorn` command & firewall |
| CORS errors | Ensure correct origin in Nginx config |
| Docker health check unhealthy | First startup takes ~15s (start_period); retry after waiting |

---

## Changelog

| Version | Date | Notes |
|---------|------|-------|
| 1.2.0 | 2026-08-26 | Added URL history system (auto-save parse + download); added `history_db.py` module; added pytest integration tests; fixed read-only filesystem cookie write error |
| 1.1.0 | 2026-08-25 | Initial URL history functionality, basic CRUD API |
| 1.0.0 | 2026-08-25 | Initial stable release. Retro black-gold UI, centralized logging, PWA hardening |

---

*Built with ❤️ using FastAPI, yt-dlp, and vanilla JS.*
