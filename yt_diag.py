import yt_dlp

url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
cookie_file = r'd:\VSCODE\PYTHON3\x_download_new\cookies\youtube.txt'

ydl_opts = {
    'quiet': False,
    'noplaylist': True,
    'cookiefile': cookie_file,
}

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = info.get('formats', [])
        video_formats = [f for f in formats if f.get('width') and f.get('height')]
        print(f"SUCCESS: {info.get('title')}")
        print(f"Found {len(video_formats)} video formats:")
        for f in video_formats[:5]:
            print(f"  {f['width']}x{f['height']} ext={f.get('ext')} acodec={f.get('acodec')}")
except Exception as e:
    print(f"FAIL: {e}")
