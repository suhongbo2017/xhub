import yt_dlp
import os
import traceback

def get_cookie_path(platform):
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    COOKIES_DIR = os.path.join(BASE_DIR, "cookies")
    new_path = os.path.join(COOKIES_DIR, f"{platform}.txt")
    if os.path.exists(new_path):
        return new_path
    return None

url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
platform = 'youtube'

ydl_opts = {
    'quiet': True,
    'noplaylist': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'http_headers': {
        'Accept-Language': 'en-US,en;q=0.9',
    },
}

cookie_path = get_cookie_path(platform)
if cookie_path:
    ydl_opts['cookiefile'] = cookie_path
    
try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        formats_raw = info.get('formats', [])
        available_formats = []
        
        # Extract meaningful formats
        unique_resolutions = set()
        
        for f in formats_raw:
            w = f.get('width')
            h = f.get('height')
            if not w or not h: continue
            
            res_key = f"{w}x{h}"
            if res_key in unique_resolutions: continue
            
            has_audio = f.get('acodec') != 'none'
            
            available_formats.append({
                "id": f.get('format_id'),
                "res": res_key,
                "note": f.get('format_note') or res_key,
                "ext": f.get('ext'),
                "need_merge": not has_audio or platform == "youtube",
                "filesize": f.get('filesize') or f.get('filesize_approx'),
                "url": f.get('url')
            })
            unique_resolutions.add(res_key)

        # Sort by resolution (area)
        available_formats.sort(key=lambda x: int(x['res'].split('x')[0]) * int(x['res'].split('x')[1]), reverse=True)

        # If no formats found, fall back to best
        if not available_formats:
            available_formats.append({
                "id": "best",
                "res": "Best",
                "note": "Default Best",
                "ext": "mp4",
                "need_merge": platform == "youtube",
                "filesize": None,
                "url": info.get('url') or info.get('webpage_url')
            })

        print("SUCCESS! Output formats:", len(available_formats))
except Exception as e:
    import traceback
    traceback.print_exc()
    print("FAIL:", e)
