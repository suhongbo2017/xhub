import flet as ft
# Now fully decoupled from yt_dlp! This acts strictly as a lightweight UI client.
import urllib.request
import os
import threading
import urllib.parse
import json
import traceback

# === 填入你的阿里云 IP 地址 ===
# 请将下面的 x.x.x.x 替换为你真实的阿里云公网 IP
SERVER_IP = "43.119.35.237"
API_URL = f"http://{SERVER_IP}:8866/api/parse"

def main(page: ft.Page):
    try:
        page.title = "X Video Downloader"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.vertical_alignment = ft.MainAxisAlignment.START
        page.scroll = ft.ScrollMode.AUTO
        
        url_input = ft.TextField(label="Enter X Video URL", expand=True)
        parse_btn = ft.ElevatedButton("Parse Video", icon=ft.icons.SEARCH)
        
        # UI Elements for video details
        video_card = ft.Column(visible=False, spacing=10)
        video_thumbnail = ft.Image(src="", border_radius=10, fit=ft.ImageFit.CONTAIN)
        video_title = ft.Text("Title: ", weight=ft.FontWeight.BOLD, size=16, no_wrap=False)
        video_quality = ft.Text("Quality: ")
        video_duration = ft.Text("Duration: ")
        
        progress_bar = ft.ProgressBar(visible=False, value=0)
        progress_text = ft.Text(visible=False, color=ft.colors.GREY_700)
        download_btn = ft.ElevatedButton("Download Video", icon=ft.icons.DOWNLOAD, visible=False, bgcolor=ft.colors.GREEN, color=ft.colors.WHITE)
        
        # Store fetched data
        video_info = {"url": "", "title": ""}
        
        def on_parse(e):
            if not url_input.value:
                page.snack_bar = ft.SnackBar(ft.Text("Please enter a URL"))
                page.snack_bar.open = True
                page.update()
                return
                
            parse_btn.disabled = True
            progress_bar.visible = True
            progress_bar.value = None # indeterminate
            progress_text.visible = True
            progress_text.value = "Connecting to backend server..."
            page.update()
            
            # run in thread to avoid blocking UI
            threading.Thread(target=extract_info).start()

        def extract_info():
            try:
                if SERVER_IP == "x.x.x.x":
                    raise Exception("Please configure your Aliyun IP in main.py first!")
                    
                req_data = json.dumps({"url": url_input.value}).encode('utf-8')
                req = urllib.request.Request(API_URL, data=req_data, headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
                
                with urllib.request.urlopen(req, timeout=30) as response:
                    # response should be the JSON structure defined in server.py
                    raw_data = response.read()
                    print("RAW DATA:", raw_data)
                    result = json.loads(raw_data.decode('utf-8'))
                    
                    if not result.get("success"):
                        raise Exception("Server failed to parse the video.")
                    
                    data = result.get("data", {})
                    
                    video_info["url"] = data.get("url")
                    video_info["title"] = data.get("title", 'x_video')
                    
                    # update UI
                    video_thumbnail.src = data.get('thumbnail', '')
                    video_title.value = f"Title: {video_info['title']}"
                    
                    quality = data.get('quality', 'best')
                    video_quality.value = f"Quality: {quality}"
                    
                    dur = data.get('duration', 0)
                    video_duration.value = f"Duration: {dur}s"
                    
                    video_card.controls = [
                        video_thumbnail,
                        video_title,
                        video_quality,
                        video_duration
                    ]
                    video_card.visible = True
                    download_btn.visible = True
                    
                    progress_bar.visible = False
                    progress_text.visible = False
                    parse_btn.disabled = False
                    
                    page.update()
                    
            except Exception as ex:
                print(f"Error: {ex}")
                progress_bar.visible = False
                progress_text.visible = False
                parse_btn.disabled = False
                page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(ex)}"))
                page.snack_bar.open = True
                page.update()

        def on_download(e):
            download_btn.disabled = True
            progress_bar.visible = True
            progress_bar.value = 0
            progress_text.visible = True
            progress_text.value = "Preparing download..."
            page.update()
            
            threading.Thread(target=download_video).start()

        def download_video():
            try:
                # We do NOT download the video directly from the internet anymore!
                # We download it via the proxy_download endpoint on the Aliyun server to bypass any headers/CORS blocks!
                video_url = video_info["url"]
                # The server's proxy_download takes video_url and title
                # Wait, our file download code here downloads natively. Let's just download directly from video_url.
                # Actually, standard MP4 links download natively perfectly via Flet's pure python request without CORS issues (mobile isn't a browser sandboxed for CORS).
                title = video_info["title"]
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                if not safe_title:
                    safe_title = "x_video"
                
                # Try finding Downloads folder
                download_dir = os.path.expanduser("~/Downloads")
                android_ext_storage = os.environ.get("EXTERNAL_STORAGE")
                if android_ext_storage:
                    download_dir = os.path.join(android_ext_storage, "Download")
                
                if not os.path.exists(download_dir):
                    download_dir = os.getcwd() # local fallback
                    
                file_path = os.path.join(download_dir, f"{safe_title}.mp4")
                
                req = urllib.request.Request(video_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                with urllib.request.urlopen(req) as response:
                    total_size = int(response.info().get('Content-Length', -1))
                    downloaded_size = 0
                    
                    with open(file_path, 'wb') as out_file:
                        while chunk := response.read(8192 * 4):
                            out_file.write(chunk)
                            downloaded_size += len(chunk)
                            if total_size > 0:
                                progress_bar.value = downloaded_size / total_size
                                progress_text.value = f"Downloaded {downloaded_size//1024//1024}MB / {total_size//1024//1024}MB"
                            else:
                                progress_bar.value = None
                                progress_text.value = f"Downloaded {downloaded_size//1024//1024}MB"
                            page.update()
                
                progress_bar.visible = False
                progress_text.value = f"Saved to: {file_path}"
                
                page.snack_bar = ft.SnackBar(ft.Text("Download Complete!"))
                page.snack_bar.open = True
                
            except Exception as ex:
                print(f"Error downloading: {ex}")
                progress_bar.visible = False
                progress_text.value = f"Error: {str(ex)}"
                page.snack_bar = ft.SnackBar(ft.Text(f"Download Error: {str(ex)}"))
                page.snack_bar.open = True
            finally:
                download_btn.disabled = False
                page.update()

        parse_btn.on_click = on_parse
        download_btn.on_click = on_download

        page.add(
            ft.Row([ft.Icon(ft.icons.VIDEO_LIBRARY, color=ft.colors.BLUE_700), ft.Text("X Video Downloader", size=24, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_700)], alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider(),
            ft.Row([url_input, parse_btn]),
            ft.Column([
                progress_bar,
                progress_text,
                video_card,
                download_btn
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )

    except Exception as e:
        page.add(ft.Text(f"CRITICAL APP ERROR:\n{traceback.format_exc()}", color=ft.colors.RED))
        page.update()

if __name__ == "__main__":
    ft.app(target=main)
