# -*- coding: utf-8 -*-
import sys
import os
import traceback
import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
import logging
from logging.handlers import RotatingFileHandler
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
import json
import asyncio
from pathlib import Path

# ==================== Advanced Logging Setup ====================
class LogFormatter(logging.Formatter):
    """Custom formatter with timestamp, level, module, line number."""
    def format(self, record):
        return f"{self.formatTime(record)} [{record.levelname:<7}] [{record.module}:{record.lineno}] {record.getMessage()}"

def setup_logger(name, log_file, level=logging.INFO, max_bytes=10*1024*1024):
    """Create a logger with rotating file handler and console output."""
    logger_obj = logging.getLogger(name)
    logger_obj.setLevel(level)
    
    # Avoid duplicate handlers
    if not logger_obj.handlers:
        formatter = LogFormatter('%(asctime)s [%(levelname)-7s] [%(module)s:%(lineno)d] %(message)s')
        
        # Rotating file handler (10MB per file, keep 5 backups)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger_obj.addHandler(file_handler)
        
        # Error-only file
        error_handler = RotatingFileHandler(
            log_file.replace('.log', '_error.log'),
            maxBytes=max_bytes,
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger_obj.addHandler(error_handler)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger_obj.addHandler(console_handler)
    
    return logger_obj

logger = setup_logger("xhub", os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server.log'))
error_logger = logging.getLogger("xhub.errors")

# ==================== App Initialization ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ==================== Error Storage (in-memory buffer) ====================
ERROR_LOG_FILE = os.path.join(BASE_DIR, 'error_report.json')
_error_buffer = []  # Keep last 200 errors in memory

def _save_errors_to_disk():
    """Persist error buffer to disk as JSON."""
    try:
        with open(ERROR_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(_error_buffer[-200:], f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# ==================== App Initialization ====================
app = FastAPI(title="X Video Downloader API", version="3.0.0-stable")

# CORS: wildcard + no credentials = no preflight needed for cross-origin POST
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Length", "X-Error-Id"],
)

# ==================== Global Exception Handler ====================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch ALL unhandled exceptions - the ultimate safety net."""
    import traceback
    import uuid
    
    error_id = str(uuid.uuid4())[:8]
    timestamp = datetime.datetime.now().isoformat()
    method = request.method
    path = request.url.path
    client_host = request.client.host if request.client else 'unknown'
    
    # Build detailed error info
    error_info = {
        "error_id": error_id,
        "timestamp": timestamp,
        "method": method,
        "path": path,
        "client": client_host,
        "exception_type": type(exc).__name__,
        "exception_message": str(exc)[:500],
        "traceback": traceback.format_exc()[:2000],
    }
    
    # Log to ERROR level (goes to both file & console)
    logger.error(
        f"[CRITICAL] {method} {path} | Client: {client_host} | ErrorID: {error_id}\n"
        f"  Exception: {type(exc).__name__}: {str(exc)[:500]}\n"
        f"  Traceback:\n{traceback.format_exc()}"
    )
    
    # Save to in-memory buffer
    _error_buffer.append(error_info)
    if len(_error_buffer) > 200:
        _error_buffer.pop(0)
    
    # Persist to disk periodically
    _save_errors_to_disk()
    
    # Return user-friendly error response
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Internal server error (ID: {error_id})",
            "error_id": error_id,
            "timestamp": timestamp
        },
        headers={"X-Error-ID": error_id}
    )


# ==================== Error Log API Endpoint ====================
@app.get("/api/error-log")
async def get_error_log(limit: int = 50):
    """Return recent errors for debugging."""
    return {"errors": list(reversed(_error_buffer[-limit:]))}



@app.on_event("startup")
async def startup_event():
    logger.info("=" * 60)
    logger.info("X HUB Server Starting...")
    logger.info(f"  Working dir: {BASE_DIR}")
    logger.info(f"  Cookie: {'OK' if os.path.exists(os.path.join(BASE_DIR, 'xcookies.txt')) else 'MISSING'}")
    logger.info(f"  Frontend: {'OK' if os.path.exists(os.path.join(BASE_DIR, 'index.html')) else 'MISSING'}")
    logger.info("=" * 60)


@app.get("/")
async def root(request: Request):
    return FileResponse(os.path.join(BASE_DIR, "index.html"))


@app.get("/manifest.json")
async def get_manifest():
    path = os.path.join(BASE_DIR, "manifest.json")
    return FileResponse(path) if os.path.exists(path) else JSONResponse(status_code=404, content={"detail": "manifest.json not found"})


@app.get("/sw.js")
async def get_sw():
    path = os.path.join(BASE_DIR, "sw.js")
    return FileResponse(path, media_type="application/javascript") if os.path.exists(path) else JSONResponse(status_code=404, content={"detail": "sw.js not found"})


def _sanitize_title(title):
    """Clean title for safe filename."""
    safe = "".join(c for c in str(title) if c.isalnum() or c in (' ', '-', '_', '.', '('))
    return safe[:100].strip() or "video"


def _get_cookie_path():
    return os.path.join(BASE_DIR, "xcookies.txt")


# ==================== PARSE ====================

@app.post("/api/parse")
async def parse_video(request: Request):
    try:
        data = await request.json()
    except Exception as e:
        logger.warning(f"[PARSE] Bad JSON from {request.client.host}: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    url = (data.get("url") or "").strip()
    if not url:
        logger.warning(f"[PARSE] No URL provided from {request.client.host}")
        raise HTTPException(status_code=400, detail="Missing URL")

    logger.info(f"[PARSE] From {request.client.host} | URL: {url[:80]}")

    cp = _get_cookie_path()
    ydl_opts = {
        'format': 'best',  # Same as original to maximize compatibility
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'nocheckcertificate': True,  # Required for proxy environments
    }
    if os.path.exists(cp) and os.path.getsize(cp) > 0:
        ydl_opts['cookiefile'] = cp

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])

            video_url = None
            is_m3u8 = False
            quality = "Best"

            # Prefer direct MP4 links
            mp4s = [f for f in formats 
                    if f.get('ext') == 'mp4' 
                    and f.get('vcodec') != 'none'
                    and 'm3u8' not in (f.get('url') or '')
                    and 'dash' not in f.get('protocol', '')]

            if mp4s:
                mp4s.sort(key=lambda f: (f.get('width', 0) or 0) * (f.get('height', 0) or 0), reverse=True)
                video_url = mp4s[0].get('url')
                w = mp4s[0].get('width', '?') or '?'
                h = mp4s[0].get('height', '?') or '?'
                quality = f"{w}x{h}"
                logger.info(f"[PARSE] Found MP4: {quality}")
            else:
                m3u8s = [f for f in formats 
                         if 'm3u8' in f.get('protocol', '') 
                         or f.get('ext') == 'm3u8']
                if m3u8s:
                    m3u8s.sort(key=lambda f: (f.get('width', 0) or 0) * (f.get('height', 0) or 0), reverse=True)
                    video_url = m3u8s[0].get('url')
                    is_m3u8 = True
                    w = m3u8s[0].get('width', '?') or '?'
                    h = m3u8s[0].get('height', '?') or '?'
                    quality = f"HLS {w}x{h}"
                    logger.info(f"[PARSE] Found HLS: {quality}")

        resp = {
            "success": True,
            "data": {
                "title": info.get('title', 'video'),
                "url": video_url or info.get('url', ''),
                "duration": int(info.get('duration', 0)) if info.get('duration') else 0,
                "thumbnail": info.get('thumbnail', ''),
                "quality": quality,
                "is_m3u8": is_m3u8,
            }
        }
        logger.info(f"[PARSE] OK | {info.get('title', '?')[:50]} | {quality} | m3u8:{is_m3u8}")
        return resp

    except Exception as e:
        msg = str(e).split('\n')[0][:200]
        logger.error(f"[PARSE] FAILED | {msg}")
        raise HTTPException(status_code=500, detail=f"Parse failed: {msg}")


# ==================== DOWNLOAD HELPERS ====================

def _merge_hls(video_url, title, cookie_path):
    """HLS merge via yt-dlp (runs in thread pool)."""
    safe_title = _sanitize_title(title)
    temp_dir = tempfile.mkdtemp(prefix='xhub_')

    try:
        out_path = os.path.join(temp_dir, f"{uuid.uuid4().hex}.mp4")
        ydl_opts = {
            'format': 'best',  # Same as original
            'outtmpl': out_path,
            'merge_output_format': 'mp4',
            'nocheckcertificate': True,
        }
        if cookie_path and os.path.exists(cookie_path):
            ydl_opts['cookiefile'] = cookie_path

        logger.info(f"[MERGE] yt-dlp merging -> {out_path}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        size = os.path.getsize(out_path) / 1024 / 1024
        logger.info(f"[MERGE] Done: {safe_title}.mp4 ({size:.1f} MB)")
        return (FileResponse(out_path, media_type="video/mp4", filename=f"{safe_title}.mp4"), temp_dir)

    except Exception as e:
        logger.warning(f"[MERGE] Cleaning up failed dir: {temp_dir}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def _proxy_mp4(video_url, title):
    """Direct MP4 proxy via urllib (runs in thread pool)."""
    safe_title = _sanitize_title(title)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0',
        'Referer': 'https://x.com/',
    }

    logger.info(f"[PROXY] Connecting to remote URL...")
    
    try:
        req = urllib.request.Request(video_url, headers=headers)
        res = urllib.request.urlopen(req, timeout=90)
        
        cl = res.getheader('Content-Length')
        if cl:
            logger.info(f"[PROXY] Content-Length: {int(cl)/1024/1024:.1f} MB")
        else:
            logger.warning("[PROXY] No Content-Length header")

        enc_name = urllib.parse.quote(safe_title)

        def stream_gen():
            try:
                while True:
                    chunk = res.read(1024 * 512)
                    if not chunk:
                        break
                    yield chunk
            except GeneratorExit:
                logger.info(f"[PROXY] Client disconnected")
            except Exception as e:
                logger.error(f"[PROXY] Stream error: {str(e)[:100]}")
                raise  # Re-raise so FastAPI knows it failed
            finally:
                try:
                    res.close()
                except:
                    pass

        resp_headers = {
            "Content-Disposition": f"attachment; filename*=UTF-8''{enc_name}.mp4",
            "Cache-Control": "no-store",
        }
        if cl:
            resp_headers["Content-Length"] = cl

        return StreamingResponse(stream_gen(), media_type="video/mp4", headers=resp_headers)

    except urllib.error.HTTPError as he:
        msg = f"Remote HTTP {he.code}: {he.reason}"
        logger.error(f"[PROXY] {msg}")
        raise Exception(msg)
    except urllib.error.URLError as ue:
        msg = f"URL error: {ue.reason}"
        logger.error(f"[PROXY] {msg}")
        raise Exception(msg)
    except Exception as e:
        msg = f"Connection error: {str(e)[:120]}"
        logger.error(f"[PROXY] {msg}")
        raise Exception(msg)


async def _cleanup_after_transfer(temp_dir):
    """Wait for transfer to complete, then clean up temp files."""
    await asyncio.sleep(2)
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.info(f"[CLEANUP] Removed: {os.path.basename(temp_dir)}")
    except Exception as e:
        logger.warning(f"[CLEANUP] Error removing {temp_dir}: {e}")


# ==================== DOWNLOAD ENDPOINT ====================

@app.post("/api/download")
async def download_video(request: Request, background_tasks: BackgroundTasks):
    """Download/merge X videos - proxy or HLS merge."""
    try:
        data = await request.json()
    except Exception as e:
        logger.warning(f"[DOWNLOAD] Bad JSON from {request.client.host}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    video_url = data.get("video_url", "")
    title = data.get("title", "video")
    is_m3u8 = bool(data.get("is_m3u8", False))

    if not video_url:
        logger.warning(f"[DOWNLOAD] Missing video_url from {request.client.host}")
        raise HTTPException(status_code=400, detail="Missing video_url")

    mode = "HLS Merge" if is_m3u8 else "MP4 Proxy"
    logger.info(f"[DOWNLOAD] From {request.client.host} | {mode} | title={title[:40]} | url={video_url[:50]}")

    try:
        loop = asyncio.get_running_loop()

        if is_m3u8:
            func = _merge_hls
            args = (video_url, title, _get_cookie_path())
        else:
            func = _proxy_mp4
            args = (video_url, title)

        logger.info(f"[DOWNLOAD] Executing {mode} in thread pool...")
        
        # Use run_in_executor with proper error propagation
        coro = loop.run_in_executor(None, func, *args)
        result = await coro

        if isinstance(result, tuple):
            file_resp, temp_dir = result
            background_tasks.add_task(_cleanup_after_transfer, temp_dir)
            logger.info(f"[DOWNLOAD] Returning merged file | temp_dir={os.path.basename(temp_dir)}")
            return file_resp
        
        logger.info("[DOWNLOAD] Returning streaming response")
        return result

    except HTTPException:
        raise
    except Exception as e:
        err_msg = str(e)
        logger.error(f"[DOWNLOAD] FAILED: {err_msg}")
        raise HTTPException(
            status_code=400,
            detail=f"Download failed: {err_msg[:250]}"
        )


# ==================== MAIN ====================
if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--config":
        BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[2]))

    logger.info("X HUB launching on http://0.0.0.0:8866")
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8866,
        workers=1,
        log_level="info",
        access_log=True,
        timeout_graceful_shutdown=5,
    )
