import yt_dlp
import os
import traceback

def get_cookie_path(platform):
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    COOKIES_DIR = os.path.join(BASE_DIR, "cookies")
    new_path = os.path.join(COOKIES_DIR, f"{platform}.txt")
    if os.path.exists(new_path):
        return new_path
    
    PLATFORM_COOKIES = {
        "x": "xcookies.txt",
        "twitter": "xcookies.txt",
        "youtube": "ytcookies.txt",
        "tiktok": "ttcookies.txt",
        "instagram": "igcookies.txt"
    }
    legacy_name = PLATFORM_COOKIES.get(platform)
    if legacy_name:
        legacy_path = os.path.join(BASE_DIR, legacy_name)
        if os.path.exists(legacy_path):
            return legacy_path
    return None

url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
platform = "youtube"

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
        print("Success, info length:", len(info))
except Exception as e:
    traceback.print_exc()
