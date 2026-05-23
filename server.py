# -*- coding: utf-8 -*-
import uvicorn
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
import yt_dlp
import os
import shutil
import tempfile
import uuid
import urllib.request
import urllib.error
import urllib.parse

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

@app.get("/sw.js")
async def get_sw():
    """提供 Service Worker (用于离线支持和 PWA 安装) / Serves the Service Worker"""
    path = os.path.join(BASE_DIR, "sw.js")
    if os.path.exists(path):
        return FileResponse(path, media_type="application/javascript")
    return JSONResponse(status_code=404, content={"detail": "sw.js not found"})

@app.post("/api/parse")
async def parse_video(request: Request):
    """
    视频解析接口 / Video Parser Endpoint
    提取视频元数据并寻找最高清的下载地址
    """
    data = await request.json()
    url = data.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Missing URL")
    
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
            else:
                # 寻找 HLS (m3u8) 流 / Look for HLS streams
                m3u8s = [f for f in formats if 'm3u8' in f.get('protocol', '') or f.get('ext') == 'm3u8']
                if m3u8s:
                    m3u8s.sort(key=lambda f: (f.get('width', 0) or 0) * (f.get('height', 0) or 0), reverse=True)
                    video_url = url 
                    is_m3u8 = True
                    quality = f"HLS {m3u8s[0].get('width', '???')}x{m3u8s[0].get('height', '???')}"
            
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/download")
def proxy_download(background_tasks: BackgroundTasks, video_url: str, title: str = "video", is_m3u8: bool = False):
    """
    下载代理与合并接口 / Download Proxy and Merge Endpoint
    1. MP4 直连通过后端转发流量，解决跨域下载问题
    2. m3u8 流由后端自动下载并使用 ffmpeg 合并为 MP4 后发送
    """
    try:
        # 文件名清理 / Title sanitization
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip() or "video"
        encoded_title = urllib.parse.quote(safe_title)

        if is_m3u8:
            # HLS 合并逻辑 / HLS Merge Logic
            temp_dir = tempfile.mkdtemp()
            out_path = os.path.join(temp_dir, f"{uuid.uuid4()}.mp4")
            ydl_opts = {'format': 'best', 'outtmpl': out_path, 'merge_output_format': 'mp4'}
            cookie_path = os.path.join(BASE_DIR, "xcookies.txt")
            if os.path.exists(cookie_path): ydl_opts['cookiefile'] = cookie_path
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([video_url])
            
            # 后端异步清理：文件发送后自动删除 / Async cleanup: delete after serving
            background_tasks.add_task(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
            return FileResponse(out_path, media_type="video/mp4", filename=f"{safe_title}.mp4")
        else:
            # MP4 代理转发 / Direct MP4 Proxy
            req = urllib.request.Request(video_url, headers={'User-Agent': 'Mozilla/5.0'})
            res = urllib.request.urlopen(req)
            def stream():
                while chunk := res.read(1024 * 64): yield chunk
                    
            headers = {"Content-Disposition": f"attachment; filename*=utf-8''{encoded_title}.mp4"}
            cl = res.getheader('Content-Length')
            if cl: headers["Content-Length"] = cl
            return StreamingResponse(stream(), media_type="video/mp4", headers=headers)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Download failed: {str(e)}")

if __name__ == "__main__":
    # 服务默认绑定在 8866 端口 / Running on port 8866 by default
    uvicorn.run("server:app", host="0.0.0.0", port=8866, reload=True)
