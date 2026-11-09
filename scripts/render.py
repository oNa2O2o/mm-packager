#!/usr/bin/env python
"""mm-packager 渲染器：timeline.json → mp4（PIL 逐帧合成 + ffmpeg 编码/混音），不依赖编辑器。

用法：
  python render.py timeline.json                 # 出成片
  python render.py timeline.json --draft         # 540x960 校对预览（快）
  python render.py timeline.json --still 3.5 8.2 # 出指定时刻静帧 PNG（看版面）

timeline.json：
{
  "size": [1080, 1920], "fps": 30, "duration": 23.4, "out": "<工程目录>/导出/xxx.mp4",
  "clips": [   // 数组顺序 = 叠放顺序，后面的在上层
    {"type": "video", "src": "abs.mp4", "start": 0, "duration": 12, "in": 0, "fit": "cover",
     "transform": {"x":0,"y":0,"scale":1,"rotation":0,"opacity":1,"anchorX":.5,"anchorY":.5},
     "keyframes": {"scale": [{"t":0,"v":1},{"t":.5,"v":1.2,"ease":"ease"}]}},
    {"type": "image", "src": "layer.png", "start": 1, "duration": 2, "fit": "fill", "keyframes": {...}},
    {"type": "sequence", "src": "dir/intro_%03d.png", "start": 0, "duration": 5, "fps": 30}   // 逐帧图层
  ],
  "audio": [ {"src": "a.wav", "start": 0, "duration": 3, "in": 0, "volume": 1, "fadeIn": 0, "fadeOut": 0} ],
  "limiter": 0.89
}
关键帧：t 为 clip 内相对秒；属性 x y（像素位移）scale scaleX scaleY rotation（度）opacity；
ease：缺省/'ease' = smoothstep，'linear'，'hold' = 保持到下一帧。缩放/旋转中心 = anchorX/anchorY（0–1）。
"""
import argparse, json, math, os, subprocess, sys
import numpy as np
from PIL import Image

DEF_TF = {"x": 0, "y": 0, "scale": 1, "scaleX": 1, "scaleY": 1, "rotation": 0, "opacity": 1, "anchorX": .5, "anchorY": .5}


def value_at(keys, t, fb):
    if not keys: return fb
    k = sorted(keys, key=lambda a: a["t"])
    if t <= k[0]["t"]: return k[0]["v"]
    for a, b in zip(k, k[1:]):
        if a["t"] <= t <= b["t"]:
            if a.get("ease") == "hold": return a["v"]
            u = (t - a["t"]) / max(1e-9, b["t"] - a["t"])
            if a.get("ease") != "linear": u = u * u * (3 - 2 * u)
            return a["v"] + (b["v"] - a["v"]) * u
    return k[-1]["v"]


def tf_at(c, lt):
    base = {**DEF_TF, **(c.get("transform") or {})}
    kf = c.get("keyframes") or {}
    return {k: (value_at(kf[k], lt, base[k]) if k in kf else base[k]) for k in base}


def probe(src):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", src], capture_output=True, text=True)
    w, h = r.stdout.strip().split("\n")[0].split(",")[:2]
    return int(w), int(h)


class VideoReader:
    """顺序读取一个视频片段（从 in 开始，按输出 fps 取帧）。"""
    def __init__(self, src, t_in, fps, dur):
        self.w, self.h = probe(src)
        self.p = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{t_in:.4f}", "-i", src, "-t", f"{dur + 1:.4f}",
                                   "-vf", f"fps={fps}", "-f", "rawvideo", "-pix_fmt", "rgba", "-"],
                                  stdout=subprocess.PIPE, stdin=subprocess.DEVNULL)
        self.n, self.last = -1, None

    def get(self, idx):
        while self.n < idx:
            buf = self.p.stdout.read(self.w * self.h * 4)
            if len(buf) < self.w * self.h * 4: break     # 源视频不够长：停在最后一帧
            self.last = Image.frombuffer("RGBA", (self.w, self.h), buf, "raw", "RGBA", 0, 1); self.n += 1
            if self.n >= idx: break
        return self.last

    def close(self):
        try: self.p.kill()
        except Exception: pass


def fit_size(fit, sw, sh, W, H):
    if fit == "fill": return W, H
    s = max(W / sw, H / sh) if fit == "cover" else min(W / sw, H / sh)
    return round(sw * s), round(sh * s)


def place(canvas, img, c, tf, W, H):
    fw, fh = fit_size(c.get("fit", "cover" if c["type"] == "video" else "fill"), img.width, img.height, W, H)
    if img.size != (fw, fh): img = img.resize((fw, fh), Image.LANCZOS)
    ox, oy = (W - fw) / 2, (H - fh) / 2                       # 适配后居中
    op = max(0., min(1., tf["opacity"]))
    if op <= 0: return
    sx, sy = tf["scale"] * tf["scaleX"], tf["scale"] * tf["scaleY"]
    if abs(sx) < 1e-4 or abs(sy) < 1e-4: return
    ident = abs(sx - 1) < 1e-6 and abs(sy - 1) < 1e-6 and abs(tf["rotation"]) < 1e-6
    if op < 1:
        a = np.asarray(img.getchannel("A"), dtype=np.float32) * op
        img = img.copy(); img.putalpha(Image.fromarray(a.astype(np.uint8)))
    if ident:
        dx, dy = round(ox + tf["x"]), round(oy + tf["y"])
        canvas.alpha_composite(img, (max(0, dx), max(0, dy)), (max(0, -dx), max(0, -dy)))
        return
    # 正变换：p' = A + T + R·S·(p - A)，A 为锚点（画布坐标）；PIL 需要逆变换
    ax, ay = ox + tf["anchorX"] * fw, oy + tf["anchorY"] * fh
    th = math.radians(tf["rotation"]); cs, sn = math.cos(th), math.sin(th)
    tx, ty = ax + tf["x"], ay + tf["y"]
    # 逆：p = A + S^-1 R^-1 (p' - T - A)
    a11, a12 = cs / sx, sn / sx
    a21, a22 = -sn / sy, cs / sy
    # 输入坐标是相对 img 左上角：p_img = p - (ox, oy)
    c0 = ax - ox - (a11 * tx + a12 * ty)
    c1 = ay - oy - (a21 * tx + a22 * ty)
    layer = img.transform((W, H), Image.AFFINE, (a11, a12, c0, a21, a22, c1), resample=Image.BILINEAR)
    canvas.alpha_composite(layer)


class Renderer:
    def __init__(self, tl, scale=1.0):
        self.tl = tl
        self.W, self.H = tl.get("size", [1080, 1920])
        self.fps = tl.get("fps", 30)
        self.clips = tl["clips"]
        self.readers, self.images = {}, {}
        self.scale = scale

    def img(self, path):
        if path not in self.images:
            if not os.path.isfile(path): sys.exit(f"找不到图片: {path}")
            self.images[path] = Image.open(path).convert("RGBA")
        return self.images[path]

    def frame(self, t, idx=None):
        W, H = self.W, self.H
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        for i, c in enumerate(self.clips):
            s, d = c["start"], c["duration"]
            if not (s - 1e-6 <= t < s + d - 1e-6): continue
            lt = t - s
            if c["type"] == "video":
                if idx is None:            # 静帧：单独抽一帧
                    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{c.get('in', 0) + lt * c.get('speed', 1):.4f}",
                                        "-i", c["src"], "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
                    import io; im = Image.open(io.BytesIO(r.stdout)).convert("RGBA")
                else:
                    if i not in self.readers:
                        self.readers[i] = VideoReader(c["src"], c.get("in", 0), self.fps, d)
                        self.readers[i].base = idx
                    im = self.readers[i].get(idx - self.readers[i].base)
                    if im is None: continue
            elif c["type"] == "sequence":
                n = int(lt * c.get("fps", self.fps) + 1e-6)
                im = self.img(c["src"] % (c.get("first", 0) + n)) if os.path.isfile(c["src"] % (c.get("first", 0) + n)) else None
                if im is None: continue
            else:
                im = self.img(c["src"])
            place(canvas, im, c, tf_at(c, lt), W, H)
        for k in [k for k, c in enumerate(self.clips) if k in self.readers and t >= c["start"] + c["duration"]]:
            self.readers.pop(k).close()
        return canvas.convert("RGB")


def audio_args(tl, dur):
    inputs, chains, labels = [], [], []
    for i, a in enumerate(tl.get("audio", [])):
        if not os.path.isfile(a["src"]): sys.exit(f"找不到音频: {a['src']}")
        inputs += ["-i", a["src"]]
        d = min(a["duration"], dur - a["start"])
        if d <= 0: continue
        f = [f"atrim=start={a.get('in', 0):.4f}:duration={d:.4f}", "asetpts=PTS-STARTPTS",
             "aresample=48000", "aformat=channel_layouts=stereo"]
        if a.get("fadeIn"): f.append(f"afade=t=in:d={a['fadeIn']}")
        if a.get("fadeOut"): f.append(f"afade=t=out:st={max(0, d - a['fadeOut']):.4f}:d={a['fadeOut']}")
        f.append(f"volume={a.get('volume', 1)}")
        ms = int(round(a["start"] * 1000)); f.append(f"adelay={ms}|{ms}")
        chains.append(f"[{i + 1}:a]{','.join(f)}[a{i}]"); labels.append(f"[a{i}]")
    if not labels: return inputs, None
    lim = tl.get("limiter", .89)
    g = ";".join(chains) + f";{''.join(labels)}amix=inputs={len(labels)}:normalize=0:dropout_transition=0,apad,atrim=duration={dur:.4f}" + \
        (f",alimiter=limit={lim}:level=false" if lim else "") + "[aout]"
    return inputs, g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("timeline"); ap.add_argument("--draft", action="store_true")
    ap.add_argument("--still", nargs="*", type=float); ap.add_argument("--out")
    a = ap.parse_args()
    tl = json.load(open(a.timeline, encoding="utf-8"))
    R = Renderer(tl)
    dur = tl.get("duration") or max(c["start"] + c["duration"] for c in tl["clips"])
    out = a.out or tl["out"]
    if a.draft and not a.out: out = os.path.splitext(out)[0] + "_draft.mp4"
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    if a.still is not None:
        base = os.path.splitext(out)[0]
        for t in a.still:
            p = f"{base}_still_{t:.2f}.png"; R.frame(t).save(p); print(p)
        return
    W, H, fps = R.W, R.H, R.fps
    ow, oh = (W // 2, H // 2) if a.draft else (W, H)
    ain, graph = audio_args(tl, dur)
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", *ain]
    if graph: cmd += ["-filter_complex", graph, "-map", "0:v", "-map", "[aout]", "-c:a", "aac", "-b:a", "192k"]
    cmd += (["-vf", f"scale={ow}:{oh}"] if a.draft else []) + ["-c:v", "libx264", "-preset", "veryfast" if a.draft else "medium",
            "-crf", "23" if a.draft else "17", "-pix_fmt", "yuv420p", "-t", f"{dur:.4f}", out]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(round(dur * fps))
    for i in range(n):
        enc.stdin.write(R.frame(i / fps, i).tobytes())
        if i % (fps * 2) == 0: print(f"\r{i}/{n}", end="", file=sys.stderr, flush=True)
    enc.stdin.close(); enc.wait()
    for r in R.readers.values(): r.close()
    print(f"\n{out}")
    sys.exit(enc.returncode)


if __name__ == "__main__":
    main()
