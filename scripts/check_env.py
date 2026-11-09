#!/usr/bin/env python
"""环境自检：python check_env.py。缺什么打印什么，全部 OK 退出码 0。"""
import importlib, os, shutil, subprocess, sys

RES = os.environ.get("MM_RES", "Z:/创新事业部/AIGC项目视频组/mm-packager资源")
bad = []
def ok(name, cond, fix):
    print(("OK   " if cond else "MISS ") + name + ("" if cond else f"  → {fix}"))
    if not cond: bad.append(name)

ok("ffmpeg / ffprobe", shutil.which("ffmpeg") and shutil.which("ffprobe"), "安装 ffmpeg 并加入 PATH")
for mod, pip in [("PIL", "pillow"), ("numpy", "numpy"), ("faster_whisper", "faster-whisper"), ("playwright", "playwright（再跑 python -m playwright install chromium）")]:
    try: importlib.import_module(mod); ok(f"python: {mod}", True, "")
    except Exception: ok(f"python: {mod}", False, f"pip install {pip}")
ok("共享资源目录 " + RES, os.path.isdir(RES), "确认 Z: 盘已映射，或设置环境变量 MM_RES 指向资源目录")
for sub in ["fonts", "sfx", "models", "jp-endcard/assets", "jp-endcard/media", "library/cards", "投放参考"]:
    ok(f"  资源/{sub}", os.path.isdir(f"{RES}/{sub}"), "从资源目录同步")
ok("elevenlabs CLI（口播/BGM/备用 ASR）", shutil.which("elevenlabs") is not None, "npm i -g @elevenlabs/cli 后 elevenlabs auth login")
chrome = r"C:/Program Files/Google/Chrome/Application/chrome.exe"
ok("Chrome（app-ui / 尾板渲染）", os.path.exists(chrome), "安装 Chrome，或 python -m playwright install chromium")
sys.exit(1 if bad else 0)
