# X Video Downloader (X HUB) - Ubuntu PWA 版本

本项目是一个专注于 Ubuntu 服务器部署的 X (Twitter) 视频下载后端服务。它被设计为提供纯粹的 Web (PWA) 体验，由 FastAPI 后端处理视频解析（基于 `yt-dlp`）和高速代理下载。

## 目录结构

- `server.py`: FastAPI 核心后端代码。
- `index.html`: Web PWA 前端界面。
- `sw.js` & `manifest.json`: PWA 服务工作线程与图标配置。
- `xcookies.txt`: Twitter 的 Cookies 文件，用于绕过反爬机制。
- `requirements.txt`: Python 依赖列表。
- `start.sh`: 自动启动和依赖安装脚本。
- `xhub.service`: Ubuntu Systemd 服务配置文件。

## Ubuntu 服务器部署指南

假设您的 Ubuntu 服务器已经安装了 Nginx 并且配置了域名和 SSL 证书。

### 1. 准备运行环境

确保系统安装了 `python3`、`python3-venv`、`python3-pip` 以及 `ffmpeg`（用于处理 m3u8 高清视频合并）。

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip ffmpeg
```

### 2. 部署代码

将本文件夹内的所有代码上传到服务器。建议放置在 `/opt/xhub` 目录下：

```bash
sudo mkdir -p /opt/xhub
# (使用 scp 或 git 拷贝代码到该目录)
cd /opt/xhub

# 赋予启动脚本执行权限
sudo chmod +x start.sh
```

### 3. 配置开机自启与守护进程 (Systemd)

打开随代码附带的 `xhub.service` 文件，确认里面的 `WorkingDirectory` 和 `ExecStart` 路径符合您的实际部署路径（默认配置为 `/opt/xhub`）。

将该服务文件复制到 systemd 目录：

```bash
sudo cp xhub.service /etc/systemd/system/
```

重新加载 systemd 并启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable xhub.service
sudo systemctl start xhub.service
```

您可以查看服务状态以确保它正在正常运行并正在监听 8866 端口：
```bash
sudo systemctl status xhub.service
```
*(注：`start.sh` 在首次运行时会自动创建虚拟环境并执行 `pip install -r requirements.txt`，所以初次启动可能需要等待几十秒完成安装)*

### 4. Nginx 反向代理配置

在您的 Nginx 配置文件中（通常位于 `/etc/nginx/sites-available/` 下），将访问请求反向代理至 8866 端口。例如：

```nginx
server {
    listen 443 ssl;
    server_name x.19831018.xyz;

    # SSL 证书配置省略...

    location / {
        proxy_pass http://127.0.0.1:8866;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
配置完成后，重启 Nginx：
```bash
sudo systemctl restart nginx
```

## 使用方法

部署完成后，在手机的 Safari 或 Chrome 浏览器中访问 `https://x.19831018.xyz`。
由于具备完整的 SSL 和 Manifest 配置，浏览器会提示您**“添加到主屏幕”**。添加后，您可以像使用原生 App 一样全屏、独立运行 X HUB 进行视频下载。

## 维护建议

如果遇到无法解析或解析画质受限的问题，说明当前的 Twitter Cookie 可能已经过期或被风控。请定期使用浏览器导出工具重新获取 Cookies，并覆盖服务器上的 `xcookies.txt` 文件。重启服务即可生效 (`sudo systemctl restart xhub.service`)。
