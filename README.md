# X Video Downloader (Pro Edition) 🚀

这是一个高度集成的 X (Twitter) 视频下载全家桶方案，支持 PWA (Web)、Android (Native) 以及 Python (GUI) 三种模式。

## 📦 项目组成 (Components)
- **PWA Web App (核心推荐)**: 由 `server.py` (后端) 和 `index.html` (前端) 组成。采用 FastAPI + Vanilla JS 架构，无需安装，支持 HLS 合并下载高清视频。
- **Android Project**: 位于 `android/` 目录，包含 Android Studio 项目代码。
- **Python GUI Prototype**: 早期开发的 `main.py` 测试工具，作为历史参考。
- **Cookies 认证**: 根目录下的 `xcookies.txt` 用于绕过 X 的年龄限制和敏感内容过滤。

## ✨ 核心特性 (Key Features)
- **高清原片（4K/1080P）**：自动分析视频解析地址，优先抓取并下载最高质量的 MP4。
- **强制下载代理**：通过后端服务器中转下载流，绕过浏览器的跨域拦截，确保 100% 弹出下载窗口。
- **HLS (m3u8) 自动合并**：对于流式视频，后端会自动下载切片并利用 `ffmpeg` 合并为完整的单 MP4 文件，保证在任何设备上都能正常播放。
- **沉浸式 PWA 体验**：适配移动端刘海屏，支持“添加到主屏幕”，享受原生 App 的流畅度和全屏体验。

## 🛠 快速上手 (Quick Start)
### 服务器部署 (Ubuntu/Aliyun)
1. **安装环境**:
   ```bash
   sudo apt update && sudo apt install ffmpeg git python3-venv -y
   ```
2. **克隆项目**:
   ```bash
   git clone https://github.com/suhongbo2017/x_download.git
   cd x_download
   ```
3. **初始化 Python 环境**:
   ```bash
   python3 -m venv venv
   ./venv/bin/pip install fastapi uvicorn yt-dlp
   ```
4. **后台运行**:
   ```bash
   nohup ./venv/bin/python3 server.py > output.log 2>&1 &
   ```

## 📂 维护说明
- **更新 Cookie**: 如果解析受限视频失败，请将从浏览器导出的 `cookies.txt` 重命名为 `xcookies.txt` 放入根目录覆盖。
- **端口与 IP**: 默认为 `8866` 端口。如果需要修改，请编辑 `server.py` 最下方。

---
**所有核心文件均已包含中英双语注释。**  
*Last updated: 2026-04-27*
