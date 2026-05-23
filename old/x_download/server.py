import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import yt_dlp
import os
import shutil
import tempfile
import uuid
import threading
import time

app = FastAPI()

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
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

@app.get("/manifest.json")
async def get_manifest():
    path = os.path.join(BASE_DIR, "manifest.json")
    if os.path.exists(path):
        return FileResponse(path)
    return JSONResponse(status_code=404, content={"detail": "manifest.json not found"})

@app.get("/sw.js")
async def get_sw():
    path = os.path.join(BASE_DIR, "sw.js")
    if os.path.exists(path):
        return FileResponse(path, media_type="application/javascript")
    return JSONResponse(status_code=404, content={"detail": "sw.js not found"})

@app.post("/api/parse")
async def parse_video(request: Request):
    data = await request.json()
    url = data.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Missing URL")
    
    # We use empty user-agent or let yt-dlp handle it.
    # X (Twitter) extraction usually works with yt-dlp but can sometimes require cookies. 
    # For a basic prototype, standard extraction is used.
    cookie_path = os.path.join(BASE_DIR, "xcookies.txt")
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'noplaylist': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'http_headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        },
        'nocheckcertificate': True,
        'ignore_no_formats_error': True,
    }
    if os.path.exists(cookie_path):
        ydl_opts['cookiefile'] = cookie_path
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Refined selection logic
            formats = info.get('formats', [])
            video_url = None
            is_m3u8 = False
            
            # 1. Try to find the best direct MP4
            direct_mp4s = [
                f for f in formats 
                if f.get('ext') == 'mp4' and f.get('vcodec') != 'none' and 
                   f.get('url') and f.get('url').startswith('http') and 'm3u8' not in f.get('url')
            ]
            
            if direct_mp4s:
                direct_mp4s.sort(key=lambda f: (f.get('width', 0) or 0) * (f.get('height', 0) or 0), reverse=True)
                video_url = direct_mp4s[0].get('url')
                quality = f"{direct_mp4s[0].get('width', '???')}x{direct_mp4s[0].get('height', '???')}"
            else:
                # 2. Try to find the best m3u8 (HLS)
                m3u8_formats = [
                    f for f in formats 
                    if 'm3u8' in f.get('protocol', '') or f.get('ext') == 'm3u8'
                ]
                if m3u8_formats:
                    # Sort by resolution
                    m3u8_formats.sort(key=lambda f: (f.get('width', 0) or 0) * (f.get('height', 0) or 0), reverse=True)
                    # We pass the original URL to the downloader to let it handle merging
                    video_url = url 
                    is_m3u8 = True
                    quality = f"HLS {m3u8_formats[0].get('width', '???')}x{m3u8_formats[0].get('height', '???')}"
            
            if not video_url:
                video_url = info.get('url') or info.get('webpage_url')
            
            if not video_url:
                raise HTTPException(status_code=400, detail="Could not extract video url")

            title = info.get('title', 'twitter_video')
            duration = info.get('duration', 0)
            thumbnail = info.get('thumbnail', '')
            
            return {
                "success": True,
                "data": {
                    "title": title,
                    "url": video_url,
                    "duration": duration,
                    "thumbnail": thumbnail,
                    "quality": quality if 'quality' in locals() else "Best",
                    "is_m3u8": is_m3u8
                }
            }
    except Exception as e:
        print(f"Error parsing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.responses import StreamingResponse
import urllib.request
import urllib.error
import urllib.parse

from fastapi import BackgroundTasks

@app.get("/api/download")
def proxy_download(background_tasks: BackgroundTasks, video_url: str, title: str = "x_video", is_m3u8: bool = False):
    """
    Proxy or merge HLS then serve
    """
    try:
        # Sanitize title
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        if not safe_title: safe_title = "x_video"
        encoded_title = urllib.parse.quote(safe_title)

        if is_m3u8:
            # Server-side merging logic
            temp_dir = tempfile.mkdtemp()
            out_path = os.path.join(temp_dir, f"{uuid.uuid4()}.mp4")
            
            ydl_opts = {
                'format': 'best',
                'outtmpl': out_path,
                'quiet': True,
                'merge_output_format': 'mp4',
            }
            
            cookie_path = os.path.join(BASE_DIR, "xcookies.txt")
            if os.path.exists(cookie_path):
                ydl_opts['cookiefile'] = cookie_path
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            
            if not os.path.exists(out_path):
                raise Exception("Conversion failed - file not generated")

            def cleanup_task():
                shutil.rmtree(temp_dir, ignore_errors=True)

            background_tasks.add_task(cleanup_task)

            return FileResponse(
                out_path,
                media_type="video/mp4",
                filename=f"{safe_title}.mp4"
            )
        else:
            # Direct proxy for MP4
            req = urllib.request.Request(video_url, headers={'User-Agent': 'Mozilla/5.0'})
            response = urllib.request.urlopen(req)
            
            def stream():
                while chunk := response.read(8192 * 4):
                    yield chunk
                    
            return StreamingResponse(
                stream(), 
                media_type="video/mp4", 
                headers={"Content-Disposition": f"attachment; filename*=utf-8''{encoded_title}.mp4"}
            )
    except Exception as e:
        print(f"Download error: {e}")
        raise HTTPException(status_code=400, detail=f"Download failed: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8866, reload=True)
