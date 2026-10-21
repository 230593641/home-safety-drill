#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键启动器：本地起服务 + 自动打开浏览器
================================================
给老师用的，双击「启动网页.bat」就会跑这个脚本：

  1. 检查文件是否齐全（index.html / knock.mp3）
  2. 检查语音依赖 edge-tts，缺了自动装一次
  3. 在 8000 端口起一个本地服务（被占用就顺延到 8001、8002…）
  4. 自动用默认浏览器打开 http://localhost:端口/

用 localhost 打开，浏览器才会允许使用麦克风。
关掉这个黑色窗口，服务就停了。
"""

import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

PORT_START = 8000
PORT_TRIES = 20


def line(ch="=", n=60):
    print(ch * n)


def check_files():
    # 网页 + audio 文件夹（敲门声 + 17 条预生成语音，缺了就没声音）
    missing = []
    if not os.path.exists(os.path.join(ROOT, "index.html")):
        missing.append("index.html")
    if not os.path.exists(os.path.join(ROOT, "audio", "knock.mp3")):
        missing.append("audio 文件夹")
    if missing:
        line()
        print("  [X] 文件不完整，缺少：" + "、".join(missing))
        print("      请把整个文件夹一起解压，不要只复制 app.py")
        line()
        input("\n  按回车键退出…")
        sys.exit(1)


def is_our_server(port):
    """8000 端口上是不是已经跑着本程序。"""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=0.6) as r:
            return b'"ok":true' in r.read()
    except Exception:
        return False


def find_port():
    for p in range(PORT_START, PORT_START + PORT_TRIES):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    return None


def ensure_edge_tts(tts_server):
    """没装 edge-tts 就自动装一次（失败也不影响打开网页）。"""
    if tts_server.EDGE_OK:
        return True

    print("[*] 第一次运行，正在安装语音依赖 edge-tts（约 10 秒）…")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check", "edge-tts"],
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
        )
    except Exception:
        pass

    try:
        import edge_tts
        tts_server.edge_tts = edge_tts
        tts_server.EDGE_OK = True
        print("[√] 语音依赖安装完成")
        return True
    except Exception:
        print("[!] 语音依赖没装上（可能没联网）。网页和文字对话照常可用，只是没有声音。")
        return False


def main():
    print()
    line()
    print("   居家安全 · 防拐骗语音演练   ——   一键启动")
    line()
    print()

    check_files()

    # 如果已经有一个在跑，直接打开浏览器
    if is_our_server(PORT_START):
        url = f"http://localhost:{PORT_START}/"
        print(f"[i] 服务已经在运行：{url}")
        print("    正在打开浏览器…（这个窗口可以关掉，不影响已启动的服务）")
        webbrowser.open(url)
        time.sleep(1.5)
        return

    import tts_server
    ensure_edge_tts(tts_server)

    port = find_port()
    if port is None:
        line()
        print("  [X] 8000-8019 端口都被占用了，请关掉其它程序再试")
        line()
        input("\n  按回车键退出…")
        sys.exit(1)

    server = tts_server.make_server(port, "127.0.0.1")
    threading.Thread(target=server.serve_forever, daemon=True).start()

    url = f"http://localhost:{port}/"

    # 等服务真正起来再开浏览器
    for _ in range(30):
        if is_our_server(port):
            break
        time.sleep(0.1)

    print(f"[√] 本地服务已启动：{url}")
    print(f"[√] 语音引擎：{'Edge TTS 已就绪' if tts_server.EDGE_OK else '未安装（无声音，仅文字）'}")
    print()
    print("    正在打开浏览器…")
    webbrowser.open(url)
    print()
    line("-")
    print("  使用方法：")
    print("    1. 页面打开后，点一下大大的「点击开始」按钮（顺便解锁声音）")
    print("    2. 会先敲门，再说话；点右上角场景按钮可换敲门人")
    print("    3. 点麦克风按钮说话，说完自动发送")
    print()
    print("  注意：")
    print("    · 必须用 http://localhost 打开，双击 index.html 麦克风用不了")
    print("    · 建议用 Microsoft Edge 打开（Chrome 的语音识别依赖谷歌，国内常连不上）")
    print("    · 声音来自随附的 mp3（audio 文件夹），不联网也能响；联网时会自动升级成 Edge TTS 真人音")
    print("    · 关掉这个黑色窗口，服务就停了")
    line("-")
    print()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n已停止，谢谢使用。")
        server.shutdown()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:                     # noqa: BLE001
        print("\n[X] 启动出错：" + repr(exc))
        input("\n按回车键退出…")
        sys.exit(1)
