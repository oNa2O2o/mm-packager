# 遮罩弹幕烘焙：原视频(24fps 480x854) -> 1080x1920 30fps，弹幕在角色遮罩后面
import subprocess, numpy as np, sys, os, json
from PIL import Image, ImageFilter
sys.path.insert(0, os.path.dirname(__file__))
from mmstyle import dm_sprite
ROOT = 'F:/钟海明/2026/2026年10月26日MM-JP-猫娘报恩/'
SRC = ROOT + '猫娘报恩.mp4'; OUT = ROOT + '包装素材v1/猫娘报恩_弹幕.mp4'
MASK = ROOT + '工作区/mask/%04d.png'
W, H, FPS, N = 1080, 1920, 30, 811
SEGS = [(0, 8.70), (8.70, 15.9667), (15.9667, 27.0333)]
DUR = 4.5
DM = [(1.2,'猫ちゃんかわいい'),(1.9,'おやつ食べてる〜'),(3.3,'え？'),(3.6,'変身したwww'),(4.2,'猫娘キタ━(ﾟ∀ﾟ)━!'),
      (5.4,'貧乏ご主人で草'),(6.0,'ご主人ディスられてて草'),(7.0,'自分の手見てるのかわいい'),
      (9.7,'シャーッ！'),(11.0,'出ていかないで！'),(12.0,'塩対応すぎる'),(13.2,'リード握ってて草'),(14.6,'お金持ちの家ってw'),(15.2,'ご主人泣いてる'),
      (16.6,'小銭www'),(17.3,'拾ってて草'),(18.4,'ツンデレ確定'),(20.2,'恩返しじゃん…'),(21.2,'尊い'),(22.3,'泣いた'),(23.2,'ご主人幸せ者'),(25.6,'ポンッで戻ったwww')]
LANES = [170, 265, 360, 1520, 1615, 1710]
# 车道分配：<2.6s 只用下方（顶部有 Logo），14.4–16 避开 360
items = []; last = {l: -9 for l in LANES}
for i, (t, s) in enumerate(DM):
    cand = [l for l in LANES if not (t < 2.6 and l < 1000) and not (14.3 < t < 16.1 and l == 360)]
    lane = min(cand, key=lambda l: (last[l] > t - 1.6, last[l]))
    last[lane] = t
    sp = dm_sprite(s, amber=(i % 3 == 1))
    seg = next(sg for sg in SEGS if sg[0] <= t < sg[1])
    items.append(dict(t=t, s=s, lane=lane, sp=sp, a=np.asarray(sp, np.float32) / 255., seg=seg))
json.dump([[d['t'], d['s'], d['lane']] for d in items], open(ROOT + '工作区/dm_lanes.json', 'w', encoding='utf-8'), ensure_ascii=False)

dec = subprocess.Popen(['ffmpeg', '-v', 'quiet', '-i', SRC, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
enc = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                        '-i', SRC, '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-crf', '14', '-preset', 'medium', '-pix_fmt', 'yuv420p',
                        '-c:a', 'aac', '-b:a', '256k', '-shortest', OUT], stdin=subprocess.PIPE)
FS = 480 * 854 * 3
cur = -1; frame = None; cache = {}
def get_src(idx):
    global cur, frame
    while cur < idx:
        b = dec.stdout.read(FS)
        if len(b) < FS: return frame
        frame = b; cur += 1
    return frame
for k in range(N):
    t = k / FPS
    si = min(int(t * 24 + 1e-6), 648)
    raw = get_src(si)
    if si not in cache:
        cache.clear()
        im = Image.frombytes('RGB', (480, 854), raw).resize((W, H), Image.LANCZOS)
        m = Image.open(MASK % si).convert('L').resize((W, H), Image.BILINEAR).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(2.5))
        cache[si] = (np.asarray(im, np.float32), 1 - np.asarray(m, np.float32) / 255.)
    base, inv = cache[si]
    out = base.copy()
    for d in items:
        a, b = d['seg']
        if not (d['t'] <= t < d['t'] + DUR and a <= t < b): continue
        p = (t - d['t']) / DUR
        sw, sh = d['sp'].size
        x = int(round(W + 10 - p * (W + sw + 20))); y = d['lane'] - sh // 2
        x0, x1 = max(x, 0), min(x + sw, W)
        if x1 <= x0: continue
        rgba = d['a'][:, x0 - x:x1 - x]
        al = rgba[..., 3:4] * 0.95 * inv[y:y + sh, x0:x1, None]
        out[y:y + sh, x0:x1] = out[y:y + sh, x0:x1] * (1 - al) + rgba[..., :3] * 255 * al
    enc.stdin.write(np.clip(out, 0, 255).astype(np.uint8).tobytes())
    if k % 100 == 0: print(k, flush=True)
enc.stdin.close(); enc.wait(); dec.kill()
print('done', OUT)
