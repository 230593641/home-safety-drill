#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地服务：静态网页 + Edge TTS 语音合成
------------------------------------------------
作用：把「防拐骗语音演练」网页和微软 Edge 的语音合成（edge-tts，免费、无需 API Key）
      一起跑在一个本地端口上，网页和接口同源，麦克风、播放都不会被浏览器拦。

一般不用直接运行本文件，双击「启动网页.bat」或运行 app.py 即可。

单独运行：
    python tts_server.py        （默认 8000 端口）

接口：
    GET /health                          → {"ok":true,"engine":"edge-tts"}
    GET /tts?text=你好&voice=zh-CN-XiaoxiaoNeural&rate=-10%&pitch=-8Hz
                                         → audio/mpeg（mp3 二进制）
    GET /                                → 网页 index.html

说明：
    · 只用标准库 http.server；edge-tts 是可选的，没装也能开网页（只是没有声音）。
    · 合成结果按「音色+语速+音调+文本」缓存，同一句话重复说不再走网络。
"""

import asyncio
import hashlib
import os
import threading
from collections import OrderedDict
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

# edge-tts 是可选依赖：没装时网页照常打开，只是语音不可用
try:
    import edge_tts
    EDGE_OK = True
except Exception:                       # noqa: BLE001
    edge_tts = None
    EDGE_OK = False

try:
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", "8000"))
MAX_TEXT = 300                     # 单次合成文本上限
CACHE_MAX = 400                    # 缓存条目上限
TIMEOUT = 20                       # 单次合成超时（秒）

_cache = OrderedDict()
_lock = threading.Lock()


async def _synth(text, voice, rate, pitch):
    """调用 edge-tts 合成，返回 mp3 字节。"""
    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    buf = bytearray()
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            buf.extend(chunk["data"])
    return bytes(buf)


def synthesize(text, voice, rate, pitch):
    if not EDGE_OK:
        raise RuntimeError("edge-tts 未安装")

    key = hashlib.md5(f"{voice}|{rate}|{pitch}|{text}".encode("utf-8")).hexdigest()

    with _lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]

    audio = asyncio.run(asyncio.wait_for(_synth(text, voice, rate, pitch), timeout=TIMEOUT))
    if not audio:
        raise RuntimeError("empty audio")

    with _lock:
        _cache[key] = audio
        if len(_cache) > CACHE_MAX:
            _cache.popitem(last=False)
    return audio


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    # ---- 通用响应头：允许跨域 ----
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/health":
            body = ('{"ok":true,"engine":"%s"}' % ("edge-tts" if EDGE_OK else "none")).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/tts":
            self.handle_tts()
            return

        super().do_GET()

    def handle_tts(self):
        if not EDGE_OK:
            self.send_error(503, "edge-tts not installed")
            return

        q = parse_qs(urlparse(self.path).query)
        text = (q.get("text", [""])[0] or "").strip()[:MAX_TEXT]
        voice = q.get("voice", ["zh-CN-XiaoxiaoNeural"])[0]
        rate = q.get("rate", ["-10%"])[0]
        pitch = q.get("pitch", ["+0Hz"])[0]

        if not text:
            self.send_error(400, "text is required")
            return

        try:
            audio = synthesize(text, voice, rate, pitch)
        except Exception as exc:                      # noqa: BLE001
            print(f"[tts] 合成失败 voice={voice} err={exc!r}", flush=True)
            self.send_error(502, "tts failed")
            return

        print(f"[tts] {voice} {rate} {pitch} len={len(text)} -> {len(audio)}B  {text[:24]}", flush=True)
        self.send_response(200)
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Content-Length", str(len(audio)))
        self.send_header("Cache-Control", "public, max-age=86400")
        self.end_headers()
        self.wfile.write(audio)

    def log_message(self, fmt, *args):                # 精简日志，只保留错误
        code = str(args[1]) if len(args) > 1 else ""
        if code.startswith(("4", "5")):
            print("[http] " + (fmt % args), flush=True)


def make_server(port=PORT, host="127.0.0.1"):
    """创建（但不启动）一个服务实例，供 app.py 复用。"""
    return ThreadingHTTPServer((host, port), Handler)


if __name__ == "__main__":
    srv = make_server(PORT)
    print("=" * 58)
    print(" 防拐骗演练 · 本地服务已启动")
    print(f" 页面地址 : http://127.0.0.1:{PORT}/")
    print(f" 语音引擎 : {'Edge TTS 已就绪' if EDGE_OK else '未安装 edge-tts（无声音）'}")
    print(" 关闭服务 : 按 Ctrl+C 或直接关掉这个窗口")
    print("=" * 58)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
