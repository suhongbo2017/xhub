# X-HUB — X/Twitter Video Downloader v1.2.0

> 一个专注于 PWA 体验的 X/Twitter 视频下载工具。  
> 基于 FastAPI + yt-dlp，支持 HLS 自动合并、离线缓存、移动端原生安装。

---

## ✨ Features

- 🎯 **一键解析** — 粘贴 X 视频链接，自动获取元数据（标题、时长、画质）
- 📥 **代理下载** — 后端代理转发，绕过 CORS & 防盗链
- 🎞️ **HLS 合并** — 自动检测 m3u8 流，ffmpeg 合并为 MP4
- 📱 **PWA 安装** — 支持添加到手机主屏幕，像原生 App 一样使用
- 🌙 **复古 UI** — 黑金配色，优雅的桌面级界面
- 📊 **历史记录** — 自动持久化所有解析与下载记录，可查询、可清空
- 🔍 **错误追踪** — 集中日志 + REST API 查看实时错误
- 🧪 **测试覆盖** — 核心链路 pytest 集成测试保障

---

## 🚀 Quick Start

### 本地运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动服务
python server.py

# 或手动指定 uvicorn
uvicorn server:app --host 0.0.0.0 --port 8866
```

### Docker 部署（推荐）

```bash
cd /opt/xhub
docker compose up -d --build
```

详细部署指南请阅读 [DEPLOY.md](DEPLOY.md)。

---

## 🗂️ 项目结构

```
xhub/
├── server.py              # FastAPI 后端核心
├── history_db.py          # 历史记录 SQLite 存储模块
├── index.html             # PWA 前端（复古 UI）
├── manifest.json          # PWA 配置
├── sw.js                  # Service Worker
├── requirements.txt       # Python 依赖
├── version.txt            # 版本号 (当前: 1.2.0)
├── .gitignore             # Git 忽略规则
├── docker-compose.yml     # Docker Compose 配置
├── Dockerfile             # Docker 构建文件
├── tests/                 # pytest 集成测试
│   └── test_url_history.py  # URL 历史功能测试
├── DEPLOY.md              # 完整部署文档
├── README.md              # 本文件
├── xhub.service           # Systemd 守护进程
├── cookies/               # Twitter Cookies 目录
└── logs/                  # 运行时日志输出
```

---

## 🔧 环境要求

| Component | Version |
|-----------|---------|
| Python | ≥ 3.9 |
| ffmpeg | Any |
| yt-dlp | Latest |
| Browser | Chrome / Firefox / Safari (modern) |

---

## 💾 历史记录

X-HUB 会自动将每次请求的原始链接和下载结果持久化到 SQLite 数据库：

- **解析时自动保存**：无论解析成功与否，原始 URL 都会被记录
- **下载时追加元数据**：下载完成后记录标题、时长、质量等信息
- **去重机制**：相同 URL 仅保留一条解析记录
- **管理接口**：通过 REST API 查询和清空历史记录

### API 端点一览

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/parse` | 解析 X 视频 URL → 返回元数据 |
| `GET`  | `/api/download?video_url=...&title=...&is_m3u8=false` | 代理下载或合并 HLS |
| `GET`  | `/api/history` | 查询所有已保存的链接记录 |
| `DELETE` | `/api/db/clear` | 清空所有历史记录 |
| `GET`  | `/api/error-log` | 查看最近 200 条错误 |
| `GET`  | `/health` | 健康检查 |
| `GET`  | `/api/version` | 返回当前版本信息 |

### Parse 请求示例

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

### History 响应示例

```bash
curl http://localhost:8866/api/history
```

Response:
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
  },
  {
    "id": 9,
    "url": "https://x.com/user/status/xyz/video/1",
    "timestamp": "2026-08-26T14:28:00",
    "status": "ok",
    "title": "",
    "duration": 0,
    "quality": "unknown",
    "is_m3u8": false,
    "source_url": ""
  }
]
```

> 说明：`id=10` 为下载记录（含完整元数据），`id=9` 为仅原始 URL 的解析记录。列表按时间倒序排列（最新优先）。

---

## 📦 Docker 部署

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

详细部署指南请阅读 [DEPLOY.md](DEPLOY.md)。

---

## ⚠️ Cookie 管理

Twitter 反爬机制会定期使 Cookies 失效。当出现解析失败时：

1. 打开浏览器 DevTools → Application → Cookies
2. 找到 Twitter 域名下的所有 cookie 值
3. 复制并保存为 `xcookies.txt`（每行一个 cookie）
4. 重启服务生效

---

## 🧪 测试

```bash
pip install pytest httpx pytest-timeout
pytest tests/test_url_history.py -v
```

当前覆盖：
- ✅ 解析自动保存到数据库
- ✅ 重复 URL 去重
- ✅ GET /api/history 返回所有记录
- ✅ 每条记录包含 required fields
- ✅ 下载后自动记录元数据（标题、时长、质量）

---

## 🛣️ Changelog

| Version | Date | Notes |
|---------|------|-------|
| 1.2.0 | 2026-08-26 | 新增 URL 历史记录系统，自动保存所有解析和下载；完善测试覆盖；修复只读文件系统下 cookie 写入错误 |
| 1.1.0 | 2026-08-25 | URL 历史功能初始版本，基础 CRUD API |
| 1.0.0 | 2026-08-25 | 初始稳定版。复古黑金 UI，中心化日志，PWA 加固 |

---

*Built with ❤️ using FastAPI, yt-dlp, and vanilla JS.*
