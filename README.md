# X Video Downloader (X HUB) - 一键部署版

一个基于 FastAPI + yt-dlp 的 X (Twitter) 视频下载服务。

## 🚀 快速部署（推荐）

### Docker（最快，5 分钟搞定）

```bash
# 1. 确保 xcookies.txt 已准备好

# 2. 一键启动
docker build -t xhub . && docker run -d --name xhub -p 8866:8866 -v $(pwd)/xcookies.txt:/app/xcookies.txt xhub

# 访问 http://localhost:8866
```

### Docker Compose（更完整）

```bash
# 创建 .env 文件（复制 .env.example）
cp .env.example .env

# 一行命令启动
docker compose up -d

# 查看日志
docker compose logs -f

# 停止
docker compose down
```

### Linux 服务器（Systemd 守护）

```bash
# 运行部署脚本
chmod +x deploy.sh && ./deploy.sh mode=systemd

# 管理服务
sudo systemctl status xhub
sudo journalctl -u xhub -f
```

### Windows 本地开发

```batch
REM 运行部署脚本
deploy.bat

REM 启动服务
uvicorn server:app --host 0.0.0.0 --port 8866
```

---

## 📋 部署方式对比

| 方式 | 适用场景 | 难度 | 速度 |
|------|---------|------|------|
| **Docker** | 生产环境、云服务器 | ⭐ | ⚡⚡⚡ |
| **Docker Compose** | 有 Nginx 等配套 | ⭐⭐ | ⚡⚡ |
| **deploy.sh** | Linux 多种模式 | ⭐ | ⚡⚡⚡ |
| **Python 直接运行** | 开发调试 | ⭐⭐ | ⚡ |

---

## 🔧 Cookie 获取方法

由于 Twitter/X 的反爬机制，需要定期更新 Cookie：

1. 打开 Chrome，登录 twitter.com
2. F12 → Network → 刷新页面 → 点击任意请求
3. Headers → Request Headers → 找到 `Cookie`
4. 复制值保存到 `xcookies.txt`（一行即可）

或者使用浏览器扩展导出：[Export Cookies](https://chrome.google.com/webstore/detail/nlfepjoapihjhhbdhlfelnkfhdgmab)

---

## 🏗️ 项目结构

```
x_download/
├── server.py          # FastAPI 后端核心
├── index.html         # Web PWA 前端界面
├── sw.js              # Service Worker (PWA)
├── manifest.json      # PWA 配置
├── requirements.txt   # Python 依赖
├── xcookies.txt       # ⚠️ Twitter Cookie（必须提供）
│
├── Dockerfile         # Docker 镜像构建文件
├── docker-compose.yml # Docker Compose 配置
├── .env.example       # 环境变量模板
├── nginx.conf         # Nginx 反向代理配置
├── deploy.sh          # 🆕 Linux 一键部署脚本
├── deploy.bat         # 🆕 Windows 部署脚本
├── start.sh           # 传统启动脚本
├── cookies/           # Cookie 备用目录
└── logs/              # 运行时日志
```

---

## 🛠️ 常见问题

### Q: 解析失败 / 画质低
A: Cookie 过期或被风控。请重新获取最新 Cookie 并覆盖 `xcookies.txt`。

### Q: 大文件下载中断
A: 检查服务器内存是否充足，建议 ≥1GB RAM。

### Q: HLS 视频无法合并
A: 确保服务器安装了 ffmpeg：`apt install ffmpeg` 或 `yum install ffmpeg`

---

## 📊 技术栈

- **后端**: FastAPI + Uvicorn
- **视频解析**: yt-dlp
- **视频处理**: FFmpeg
- **前端**: Vanilla HTML/CSS/JS (PWA)
- **容器化**: Docker

---

## 🔒 安全提示

生产环境建议使用：
1. HTTPS（Let's Encrypt 免费证书）
2. Nginx 反向代理
3. 考虑添加密码保护
