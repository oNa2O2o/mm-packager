"""MM 产品 UI 模板（剧情之后的「软件功能展示」与尾板）：chat 聊天界面 / swipe 划卡选角色。1080×1920，30 fps。

用法：
  python appui.py stills --config cfg.json --out <dir> [--times 1,2.5,4]      # 先看静帧（不给 times 自动取 6 帧）
  python appui.py render --config cfg.json --out <out.mp4>                    # 渲染成片（含音效，无 BGM/口播）

配置格式见 README.md。图片路径写绝对路径。屏幕文字只来自配置（空 = 不画）。
"""
import argparse, base64, functools, hashlib, json, os, random, string, subprocess, sys, threading, time, urllib.parse, urllib.request
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
ENGINE = f"{HERE}/engine"
RES = os.environ.get("MM_RES", "Z:/创新事业部/AIGC项目视频组/mm-packager资源")   # 共享资源目录（字体/音效/尾板素材）
SHARED = f"{RES}/jp-endcard"                 # 复用 JP 尾板的字体 / Logo / 商店标 / 音效
AUD = f"{SHARED}/media/audio"
CHROME = r"C:/Program Files/Google/Chrome/Application/chrome.exe"
FPS = 30

def prepare(user):
    cfg = json.loads(json.dumps(user)); files = {}
    A = f"{SHARED}/assets"
    shared = {"fonts/black.otf": f"{A}/fonts/NotoSansJP-Black.otf", "fonts/bold.otf": f"{A}/fonts/NotoSansJP-Bold.otf",
              "fonts/medium.otf": f"{A}/fonts/NotoSansJP-Medium.otf", "a/logo_icon.png": f"{A}/logo_icon.png",
              "a/logo_word.png": f"{A}/logo_word.png", "a/badges.png": f"{A}/badges.png"}
    files.update(shared)
    cfg["fonts"] = {"black": "fonts/black.otf", "bold": "fonts/bold.otf", "medium": "fonts/medium.otf"}
    cfg["assets"] = {"logoIcon": "a/logo_icon.png", "logoWord": "a/logo_word.png", "badges": "a/badges.png"}
    def reg(v):
        p = os.path.abspath(v).replace("\\", "/")
        if not os.path.isfile(p): sys.exit(f"找不到图片: {p}")
        key = "img/" + hashlib.sha1(p.encode()).hexdigest()[:12] + os.path.splitext(p)[1].lower()
        files[key] = p; return key
    def fix(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("image", "bg") and isinstance(v, str): o[k] = reg(v)
                elif k == "gallery" and isinstance(v, list): o[k] = [reg(x) for x in v]
                else: fix(v)
        elif isinstance(o, list):
            for v in o: fix(v)
    fix(cfg)
    return cfg, files

def serve(cfg, files):
    js = ("window.APPUI_CONFIG = " + json.dumps(cfg, ensure_ascii=False) + ";").encode("utf-8")
    class H(SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_GET(self):
            path = urllib.parse.unquote(self.path.split("?")[0]).lstrip("/")
            if path == "config.js": b = js
            elif path in files: b = open(files[path], "rb").read()
            else: return super().do_GET()
            self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(H, directory=ENGINE))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_address[1]}/index.html"

class Page:
    def __init__(self, user):
        from playwright.sync_api import sync_playwright
        self.cfg, files = prepare(user); url = serve(self.cfg, files)
        self.pw = sync_playwright().start()
        self.b = self.pw.chromium.launch(executable_path=CHROME if os.path.exists(CHROME) else None)
        self.pg = self.b.new_page(viewport={"width": 540, "height": 960})
        self.pg.goto(url); self.pg.wait_for_function("window.__ready || window.__err", timeout=120000)
        err = self.pg.evaluate("window.__err")
        if err: sys.exit("引擎初始化失败: " + err)
        self.tl = self.pg.evaluate("window.timeline()")
    def frame(self, t): return base64.b64decode(self.pg.evaluate(f"window.grabFrame({t})").split(",", 1)[1])
    def close(self): self.b.close(); self.pw.stop()

def stills(user, out, times):
    os.makedirs(out, exist_ok=True); P = Page(user); D = P.tl["duration"]
    if not times: times = [round(D * k / 6, 2) for k in range(1, 6)] + [round(D - .1, 2)]
    for t in times: open(f"{out}/t{t:05.2f}.png", "wb").write(P.frame(t))
    P.close(); print(json.dumps({"stills": out, "times": times, **P.tl}, ensure_ascii=False))

SFX = {"message": ("sfx_message_1.mp3", .32), "send": ("sfx_click_1.mp3", .35), "click": ("sfx_click_1.mp3", .7),
       "hero": ("sfx_toggle_2.mp3", .4), "flash": ("sfx_intro_2.mp3", .45), "open": ("sfx_toggle_2.mp3", .35), "swipe": (None, .22)}

def render(user, out):
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    P = Page(user); D = P.tl["duration"]; n = int(round(D * FPS)); silent = out[:-4] + "_无声.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "png", "-i", "-",
                           "-vf", "scale=out_range=tv:out_color_matrix=bt709,format=yuv420p", "-c:v", "libx264", "-crf", "15", "-preset", "medium", silent], stdin=subprocess.PIPE)
    t0 = time.time()
    for i in range(n):
        ff.stdin.write(P.frame(i / FPS))
        if i % 60 == 0: print(f"frame {i}/{n} {time.time() - t0:.0f}s", flush=True)
    ff.stdin.close(); ff.wait(); P.close()
    # 音效
    inputs, fl, lab = ["-i", silent], [], []
    for j, ev in enumerate(P.tl["events"]):
        name, at = ev[0], max(0, ev[1])
        f, v = SFX.get(name, (None, 0))
        if name == "swipe":     # 合成轻柔划过声（滤波噪声，0.22 s）
            inputs += ["-f", "lavfi", "-t", "0.24", "-i", "anoisesrc=c=pink:r=48000:a=0.5"]
            k = len(inputs) // 2 - 1 if False else None
        elif f: inputs += ["-i", f"{AUD}/{f}"]
        else: continue
        idx = sum(1 for x in inputs if x == "-i") - 1
        extra = "highpass=f=600,lowpass=f=5000,afade=t=in:d=0.08,afade=t=out:st=0.08:d=0.16," if name == "swipe" else "lowpass=f=10000,"
        fl.append(f"[{idx}:a]aresample=48000,{extra}volume={v},adelay={int(at * 1000)}:all=1[s{j}]"); lab.append(f"[s{j}]")
    if lab:
        fl.append("".join(lab) + f"amix=inputs={len(lab)}:normalize=0,apad,atrim=0:{D},alimiter=limit=0.89[a]")
        amap = ["-map", "[a]", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
        fc = ["-filter_complex", ";".join(fl)]
    else:
        inputs += ["-f", "lavfi", "-t", str(D), "-i", "anullsrc=r=48000:cl=stereo"]; amap = ["-map", "1:a", "-c:a", "aac"]; fc = []
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, *fc, "-map", "0:v", *amap, "-c:v", "copy", "-t", str(D), "-movflags", "+faststart", out], check=True)
    os.remove(silent); print(json.dumps({"ok": True, "out": out, **P.tl}, ensure_ascii=False)); return out, D

def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("stills"); a.add_argument("--config", required=True); a.add_argument("--out", required=True); a.add_argument("--times")
    b = sp.add_parser("render"); b.add_argument("--config", required=True); b.add_argument("--out", required=True)
    x = ap.parse_args(); user = json.load(open(x.config, encoding="utf-8"))
    if x.cmd == "stills": stills(user, x.out, [float(v) for v in x.times.split(",")] if x.times else None)
    elif x.cmd == "render": render(user, os.path.abspath(x.out).replace("\\", "/"))

if __name__ == "__main__": main()
