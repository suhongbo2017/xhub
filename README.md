# X-HUB v1.0.0 — X (Twitter) Video Downloader

> 一个专注于 PWA 体验的 X/Twitter 视频下载工具。  
> 基于 FastAPI + yt-dlp，支持 HLS 自动合并、离线缓存、移动端原生安装。

---

## ✨ Features

- 🎯 **一键解析** — 粘贴 X 视频链接，自动获取元数据
- 📥 **代理下载** — 后端代理转发，绕过 CORS & 防盗链
- 🎞️ **HLS 合并** — 自动检测 m3u8 流，ffmpeg 合并为 MP4
- 📱 **PWA 安装** — 支持添加到手机主屏幕，像原生 App 一样使用
- 🌙 **复古 UI** — 黑金配色，优雅的桌面级界面
- 🔍 **错误追踪** — 集中日志 + REST API 查看实时错误
- 💾 **历史记录** — localStorage 持久化，随时回溯已下载内容

---

## 📸 Preview

| Parser | Downloading | History |
|--------|-------------|---------|
| ![](https://via.placeholder.com/300x500/1a1a1a/ffd700?text=X-HUB+Parser) | ![](https://via.placeholder.com/300x500/1a1a1a/ffd700?text=X-HUB+Download) | ![](https://via.placeholder.com/300x500/1a1a1a/ffd700?text=X-HUB+History) |

*(Replace with real screenshots in production)*

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

### 浏览器访问

打开 `http://localhost:8866`，粘贴 X 视频链接即可开始解析下载。

---

## 📦 Docker 部署

```bash
docker build -t xhub:v1.0.0 .
docker run -d --name xhub -p 8866:8866 -v ./xcookies.txt:/app/xcookies.txt:ro xhub:v1.0.0
```

详细部署指南请阅读 [DEPLOY.md](DEPLOY.md)。

---

## 🗂️ 项目结构

```
xhub/
├── server.py              # FastAPI 后端核心
├── index.html             # PWA 前端（复古 UI）
├── manifest.json          # PWA 配置
├── sw.js                  # Service Worker v1.0.0
├── requirements.txt       # Python 依赖
├── version.txt            # 版本号
├── .gitignore             # Git 忽略规则
├── DEPLOY.md              # 完整部署文档
├── docker-compose.yml     # Docker Compose 配置
├── Dockerfile             # Docker 构建文件
├── xhub.service           # Systemd 守护进程
└── cookies/               # Twitter Cookies 目录
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

## ⚠️ Cookie 管理

Twitter 反爬机制会定期使 Cookies 失效。当出现解析失败时：

1. 打开浏览器 DevTools → Application → Cookies
2. 找到 Twitter 域名下的所有 cookie 值
3. 复制并保存为 `xcookies.txt`（每行一个 cookie）
4. 重启服务生效

---

## 🛠️ API 接口

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/parse` | 解析视频 URL |
| GET  | `/api/download` | 代理下载视频 |
| GET  | `/api/error-log` | 查看最近 200 条错误 |

---

## 📜 License

MIT License — feel free to fork & modify.

---

*Powered by FastAPI, yt-dlp, vanilla JS.*  
*Version 1.0.0 · 2026-08-25*
