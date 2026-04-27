# -*- coding: utf-8 -*-
import flet as ft
# 早期 Flet 原型版 / Early Flet Prototype
# 现在作为独立的 UI 客户端运行，通过 API 进行解析
# This acts strictly as a lightweight UI client decoupled from the server.
import urllib.request
import os
import threading
import urllib.parse
import json
import traceback

# === 填入你的阿里云 IP 地址 / Fill in your Aliyun IP ===
# 请将下面的 x.x.x.x 替换为你真实的阿里云公网 IP
SERVER_IP = "43.119.35.237"
API_URL = f"http://{SERVER_IP}:8866/api/parse"

def main(page: ft.Page):
    """
    Flet UI 主入口 (早期原型逻辑)
    Flet UI main entrance (Legacy logic)
    """
    try:
        page.title = "X Video Downloader"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.vertical_alignment = ft.MainAxisAlignment.START
        page.scroll = ft.ScrollMode.AUTO

        # 视频链接输入框 / Video URL input field
        url_input = ft.TextField(
            label="X Video URL", 
            width=600, 
            hint_text="https://x.com/username/status/..."
        )
        # 解析进度提示 / Parsing status
        status_text = ft.Text("")
        # 结果显示列表 / Result display container
        result_container = ft.Column()

        def parse_click(e):
            """解析按钮点击回调 / Click callback for 'Parse' button"""
            if not url_input.value:
                return
            
            status_text.value = "正在解析... / Parsing..."
            status_text.color = ft.colors.BLUE
            result_container.controls.clear()
            page.update()

            def do_parse():
                try:
                    # 调用云端 API 进行解析 / Call cloud API
                    req = urllib.request.Request(
                        API_URL, 
                        data=json.dumps({"url": url_input.value}).encode(),
                        headers={"Content-Type": "application/json"}
                    )
                    with urllib.request.urlopen(req) as response:
                        res_data = json.loads(response.read().decode())
                    
                    if res_data.get("success"):
                        data = res_data["data"]
                        # 显示解析到的视频信息 / Display parsed video info
                        result_container.controls.append(
                            ft.Card(
                                content=ft.Container(
                                    padding=20,
                                    content=ft.Column([
                                        ft.Text(f"Title: {data['title']}", weight=ft.FontWeight.BOLD),
                                        ft.Text(f"Quality: {data.get('quality', 'Best')}"),
                                        ft.ElevatedButton("下载视频 / START DOWNLOAD", on_click=lambda _: os.start_browser(data['url']))
                                    ])
                                )
                            )
                        )
                        status_text.value = "解析成功! / Parse Success!"
                        status_text.color = ft.colors.GREEN
                    else:
                        status_text.value = f"解析失败: {res_data.get('detail')}"
                        status_text.color = ft.colors.RED
                except Exception as ex:
                    status_text.value = f"Error: {str(ex)}"
                    status_text.color = ft.colors.RED
                
                page.update()

            threading.Thread(target=do_parse).start()

        # UI 布局布局 / UI Layout
        page.add(
            ft.Column([
                ft.Row([url_input, ft.ElevatedButton("解析 / PARSE", on_click=parse_click)]),
                status_text,
                result_container
            ], alignment=ft.MainAxisAlignment.CENTER)
        )
    except Exception:
        print(traceback.format_exc())

if __name__ == "__main__":
    ft.app(target=main)
