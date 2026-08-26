# -*- coding: utf-8 -*-
# X-HUB v1.0.0 — FastAPI Backend
import sys
import os
import traceback
import datetime
import logging
from logging.handlers import RotatingFileHandler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
import yt_dlp
import shutil
import tempfile
import uuid
import urllib.request
import urllib.error
import urllib.parse
from history_db import save_url, get_all, clear, save_download

# ==================== Logging Setup ====================
class LogFormatter(logging.Formatter):
    """自定义日志格式化器，包含模块名和行号"""
    def format(self, record):
        return f"{self.formatTime(record)} [{record.levelname:<7}] [{os.path.basename(getattr(record,'module','?'))}:{record.lineno}] {record.getMessage()}"

def setup_logger(name, log_file, level=logging.INFO, max_bytes=10*1024*1024):
    """创建带轮转文件的 logger"""
    logger_obj = logging.getLogger(name)
    logger_obj.setLevel(level)
    if not logger_obj.handlers:
        formatter = LogFormatter('%(asctime)s [%(levelname)-7s] [%(module)s:%(lineno)d] %(message)s')
        
        # 主日志文件（INFO 级别以上）
        file_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=5, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger_obj.addHandler(file_handler)
        
        # 错误日志文件（仅 ERROR 级别）
        error_handler = RotatingFileHandler(log_file.replace('.log', '_error.log'), maxBytes=max_bytes, backupCount=5, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger_obj.addHandler(error_handler)
        
        # 控制台输出
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger_obj.addHandler(console_handler)
    return logger_obj

logger = setup_logger("xhub", os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server.log'))

# ==================== Error Tracking ====================
ERROR_LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'error_report.json')
_error_buffer = []  # 内存中保留最近 200 条错误记录

def _save_errors_to_disk():
    """将错误缓冲区持久化到磁盘"""
    try:
        import json
        with open(ERROR_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(_error_buffer[-200:], f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# 初始化 FastAPI 应用 / Initialize FastAPI
app = FastAPI(title="X Video Downloader API")

# 配置跨域 (CORS) / Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.get("/")
async def root():
    """提供 PWA 前端界面 / Serves the PWA frontend"""
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

@app.get("/manifest.json")
async def get_manifest():
    """提供 PWA 配置文件 / Serves the PWA manifest"""
    path = os.path.join(BASE_DIR, "manifest.json")
    if os.path.exists(path):
        return FileResponse(path)
    return JSONResponse(status_code=404, content={"detail": "manifest.json not found"})

# ==================== Version Info ====================
def _read_version():
    try:
        with open(os.path.join(BASE_DIR, 'version.txt'), 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return 'dev'

APP_VERSION = _read_version()

@app.get("/api/version")
async def get_version():
    """返回当前版本号 / Returns current version info"""
    return {"version": APP_VERSION, "name": "X-HUB", "platform": "Python/FastAPI"}

@app.get("/health")
async def health_check():
    """健康检查 / Health check"""
    return {"status": "ok", "version": APP_VERSION}

@app.post("/api/parse")
async def parse_video(request: Request):
    """
    视频解析接口 / Video Parser Endpoint
    提取视频元数据并寻找最高清的下载地址
    """
    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"[PARSE] Bad JSON from {request.client.host}: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    url = data.get("url")
    if not url:
        logger.warning(f"[PARSE] Missing URL from {request.client.host}")
        raise HTTPException(status_code=400, detail="Missing URL")
    
    logger.info(f"[PARSE] From {request.client.host} | URL: {url[:80]}")
    
    # 无论解析是否成功，都把原始链接持久化到本地数据库
    try:
        uid = save_url(url)
        logger.info(f"[HISTORY] Saved url id={uid} | {url[:80]}")
    except Exception as e:
        logger.warning(f"[HISTORY] Failed to save url: {e}")
    
    # 查找本地是否有 Cookies 文件 / Check for local cookies file
    cookie_path = os.path.join(BASE_DIR, "xcookies.txt")
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'noplaylist': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'nocheckcertificate': True,
    }
    if os.path.exists(cookie_path):
        ydl_opts['cookiefile'] = cookie_path
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            video_url = None
            is_m3u8 = False
            
            # 高清选择策略：优先寻找直连 MP4 / Priority: Direct MP4
            mp4s = [f for f in formats if f.get('ext') == 'mp4' and f.get('vcodec') != 'none' and 'm3u8' not in (f.get('url') or '')]
            if mp4s:
                mp4s.sort(key=lambda f: (f.get('width', 0) or 0) * (f.get('height', 0) or 0), reverse=True)
                video_url = mp4s[0].get('url')
                quality = f"{mp4s[0].get('width', '???')}x{mp4s[0].get('height', '???')}"
                logger.info(f"[PARSE] Found MP4: {quality}")
            else:
                # 寻找 HLS (m3u8) 流 / Look for HLS streams
                m3u8s = [f for f in formats if 'm3u8' in f.get('protocol', '') or f.get('ext') == 'm3u8']
                if m3u8s:
                    m3u8s.sort(key=lambda f: (f.get('width', 0) or 0) * (f.get('height', 0) or 0), reverse=True)
                    video_url = url 
                    is_m3u8 = True
                    quality = f"HLS {m3u8s[0].get('width', '???')}x{m3u8s[0].get('height', '???')}"
                    logger.info(f"[PARSE] Found HLS: {quality}")
            
            logger.info(f"[PARSE] OK | {info.get('title', '?')[:50]} | {quality} | m3u8:{is_m3u8}")
            
            return {
                "success": True,
                "data": {
                    "title": info.get('title', 'video'),
                    "url": video_url or info.get('url'),
                    "duration": info.get('duration', 0),
                    "thumbnail": info.get('thumbnail', ''),
                    "quality": quality if 'quality' in locals() else "Best",
                    "is_m3u8": is_m3u8
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e).split('\n')[0][:200]
        logger.error(f"[PARSE] FAILED | {msg}")
        raise HTTPException(status_code=500, detail=f"Parse failed: {msg}")

@app.get("/api/download")
def proxy_download(background_tasks: BackgroundTasks, video_url: str, title: str = "video", is_m3u8: bool = False):
    """
    下载代理与合并接口 / Download Proxy and Merge Endpoint
    1. MP4 直连通过后端转发流量，解决跨域下载问题
    2. m3u8 流由后端自动下载并使用 ffmpeg 合并为 MP4 后发送
    """
    # 文件名清理（需在所有分支前定义）
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip() or "video"
    encoded_title = urllib.parse.quote(safe_title)

    parsed_info = {}
    try:
        logger.info(f"[DOWNLOAD] From {video_url[:50]}... | {title[:40]} | m3u8:{is_m3u8}")
        
        # 解析视频 URL 提取时长等元数据
        ydl_opts_meta = {'quiet': True, 'noplaylist': True, 'extract_flat': False}
        cookie_path = os.path.join(BASE_DIR, "xcookies.txt")
        if os.path.exists(cookie_path): ydl_opts_meta['cookiefile'] = cookie_path
        try:
            with yt_dlp.YoutubeDL(ydl_opts_meta) as ydl:
                meta = ydl.extract_info(video_url, download=False)
                parsed_info = {
                    "title": meta.get('title', title),
                    "duration": meta.get('duration', 0),
                    "thumbnail": meta.get('thumbnail', ''),
                }
        except Exception as e:
            logger.warning(f"[DOWNLOAD] Could not fetch metadata: {e}")

        if is_m3u8:
            logger.info(f"[MERGE] Starting HLS merge...")
            # HLS 合并逻辑 / HLS Merge Logic
            temp_dir = tempfile.mkdtemp()
            out_path = os.path.join(temp_dir, f"{uuid.uuid4()}.mp4")
            ydl_opts = {'format': 'best', 'outtmpl': out_path, 'merge_output_format': 'mp4'}
            cookie_path = os.path.join(BASE_DIR, "xcookies.txt")
            if os.path.exists(cookie_path): ydl_opts['cookiefile'] = cookie_path
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([video_url])
            except Exception as e:
                err_msg = str(e).lower()
                if 'readonly' in err_msg or 'read-only' in err_msg or 'errno 30' in err_msg:
                    logger.warning(f"[MERGE] Ignoring non-fatal cookie write error: {e}")
                    # Try re-download without cookies on readonly filesystem
                    ydl_opts_nocookie = {k: v for k, v in ydl_opts.items() if k != 'cookiefile'}
                    with yt_dlp.YoutubeDL(ydl_opts_nocookie) as ydl2: ydl2.download([video_url])
                else:
                    raise
            
            size_mb = os.path.getsize(out_path) / 1024 / 1024
            logger.info(f"[MERGE] Done: {safe_title}.mp4 ({size_mb:.1f} MB)")
            
            # 保存下载记录到历史（使用传入的 title 参数，避免 yt-dlp 对直连 URL 提取错误标题）
            _log_download(title, parsed_info.get("duration", 0), is_m3u8, video_url)
            
            # 后端异步清理：文件发送后自动删除 / Async cleanup: delete after serving
            background_tasks.add_task(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
            return FileResponse(out_path, media_type="video/mp4", filename=f"{safe_title}.mp4")
        else:
            logger.info(f"[PROXY] Connecting to remote URL...")
            # MP4 代理转发 / Direct MP4 Proxy
            req = urllib.request.Request(video_url, headers={'User-Agent': 'Mozilla/5.0'})
            res = urllib.request.urlopen(req, timeout=90)
            
            cl = res.getheader('Content-Length')
            if cl:
                logger.info(f"[PROXY] Content-Length: {int(cl)/1024/1024:.1f} MB")
            else:
                logger.warning("[PROXY] No Content-Length header")
            
            def stream():
                try:
                    while chunk := res.read(1024 * 64): yield chunk
                except GeneratorExit:
                    logger.info("[PROXY] Client disconnected")
                finally:
                    res.close()
                    
            headers = {"Content-Disposition": f"attachment; filename*=utf-8''{encoded_title}.mp4"}
            if cl: headers["Content-Length"] = cl
            
            # 保存代理转发记录（使用传入的 title 参数）
            _log_download(title, parsed_info.get("duration", 0), False, video_url)
            logger.info(f"[DOWNLOAD] Returning streaming response")
            return StreamingResponse(stream(), media_type="video/mp4", headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        err_msg = str(e)[:200]
        logger.error(f"[DOWNLOAD] FAILED: {err_msg}")
        raise HTTPException(status_code=400, detail=f"Download failed: {err_msg}")

# ==================== Download Tracker Helper ====================
def _log_download(title: str, duration: int, is_m3u8: bool, source_url: str):
    """Append a download result to history."""
    safe_title = title or "video"
    logger.info(f"[HISTORY] Recording download: title={safe_title[:40]} dur={duration}")
    try:
        save_download({
            "url": source_url,
            "title": safe_title,
            "duration": duration,
            "quality": "HLS" if is_m3u8 else "MP4",
            "is_m3u8": is_m3u8,
            "source_url": source_url,
        })
    except Exception as e:
        logger.warning(f"[HISTORY] Failed to log download: {e}")

# ==================== Global Exception Handler ====================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """捕获所有未处理的异常，确保不会 500 崩溃"""
    import uuid as _uu
    error_id = str(_uu.uuid4())[:8]
    timestamp = datetime.datetime.now().isoformat()
    
    logger.error(
        f"[CRITICAL] {request.method} {request.url.path} | ErrorID: {error_id}\n"
        f"  Exception: {type(exc).__name__}: {str(exc)[:500]}\n"
        f"  Traceback:\n{traceback.format_exc()}"
    )
    
    # 保存到内存缓冲区
    error_info = {
        "error_id": error_id,
        "timestamp": timestamp,
        "method": request.method,
        "path": request.url.path,
        "exception_type": type(exc).__name__,
        "exception_message": str(exc)[:500],
        "traceback": traceback.format_exc()[:2000],
    }
    _error_buffer.append(error_info)
    if len(_error_buffer) > 200:
        _error_buffer.pop(0)
    
    # 定期持久化到磁盘
    _save_errors_to_disk()
    
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error (ID: {error_id})"},
        headers={"X-Error-ID": error_id}
    )

# ==================== Debug API ====================
@app.get("/api/error-log")
async def get_error_log(limit: int = 50):
    """返回最近的错误记录（用于调试）"""
    return {"errors": list(reversed(_error_buffer[-limit:]))}

# ==================== URL History API ====================
@app.get("/api/history")
def list_history():
    """返回所有已保存的链接记录 / Returns all saved URL records"""
    return get_all()

@app.delete("/api/db/clear")
def db_clear():
    """清空历史记录 / Clear all history records"""
    clear()
    return {"status": "cleared"}

if __name__ == "__main__":
    # 服务默认绑定在 8866 端口 / Running on port 8866 by default
    logger.info("=" * 60)
    logger.info("X HUB Server Starting...")
    logger.info(f"  Working dir: {BASE_DIR}")
    logger.info(f"  Cookie: {'OK' if os.path.exists(os.path.join(BASE_DIR, 'xcookies.txt')) else 'MISSING'}")
    logger.info(f"  Frontend: {'OK' if os.path.exists(os.path.join(BASE_DIR, 'index.html')) else 'MISSING'}")
    logger.info("=" * 60)
    
    uvicorn.run("server:app", host="0.0.0.0", port=8866, reload=True)
