# timeline.json 与图层规则

格式权威说明见 `scripts/render.py` 文件头。要点：

```json
{"size":[1080,1920],"fps":30,"duration":23.4,"out":"<工程>/导出/<名>.mp4","limiter":0.89,
 "clips":[
  {"type":"video","src":"<工程>/素材/视频_3_1080.mp4","start":0,"duration":12.03,"in":0,"fit":"cover",
   "keyframes":{"scale":[{"t":11.4,"v":1},{"t":12.0,"v":1.35,"ease":"ease"}]}},
  {"type":"image","src":"<工程>/包装素材v2/sub0.png","start":4.0,"duration":2.2,
   "keyframes":{"opacity":[{"t":0,"v":0},{"t":0.15,"v":1}]}},
  {"type":"sequence","src":"<工程>/包装素材v2/intro_%03d.png","start":0,"duration":4.45,"fps":30},
  {"type":"video","src":"<工程>/包装素材_产品UI/产品UI-划卡_v2.mp4","start":12.03,"duration":5.47}
 ],
 "audio":[
  {"src":"<工程>/素材/视频_3_1080.mp4","start":0,"duration":12.03,"in":0,"volume":1},
  {"src":"<工程>/包装素材v2/audio/bgm.mp3","start":0,"duration":23.4,"volume":0.25,"fadeOut":0.6}
 ]}
```
- clips 数组顺序 = 叠放顺序（后面在上层）。第一条应是铺满全片的画面（规则 6）。
- 关键帧 `t` 为 clip 内相对秒；属性 `x y scale scaleX scaleY rotation opacity`；`ease` 缺省平滑、`linear`、`hold`（硬闪/数值跳变）。缩放中心 `anchorX/anchorY`（0–1，相对图层）。
- `fit`：video 默认 `cover`，image 默认 `fill`（整画布 PNG 直接对齐）。
- 进度条填充：`scaleX` 关键帧 + `anchorX` 设在条左端。
- 时间先吸附到 1/30 s 再累加，避免相邻片段半帧缝。
- BGM 闪避：拆成多段 audio 条目，各自 volume，用 fadeIn/fadeOut 衔接。
- 同一视频的原声：audio 用同一 src、同 in/start/duration；删掉某段原声 = 拆成两条中间留空。

## 静帧看版面
`render.py --still t1 t2 …` 几秒出图，定稿前反复用；ffmpeg hstack 拼一张再 read。

## 环境坑（本机）
- faster-whisper GPU：RTX 5070 + `nvidia-cublas-cu12`、`nvidia-cudnn-cu12==9.*`，`zz_nvidia_dll_path.pth` 加 DLL 路径；偶发 segfault → CPU int8。
- torch CUDA `is_available()` 会 access violation：rembg 走 CPU（`u2net_human_seg`）；动漫抠图可试 `ZhengPeng7/BiRefNet_lite`。
- OpenCV 系统是 5.0 无 CascadeClassifier → `pip install opencv-python-headless==4.10.0.84 --target C:/Users/zhonghaiming5328/cv4`；模型 `$RES/models/{yunet.onnx,anime.xml}`。
- Git Bash 循环跑 ffmpeg 加 `-nostdin`；`python -I` 会忽略 PYTHONIOENCODING，中文输出写 UTF-8 文件再读。
- read 读图偶发 ENOENT：复制到 `C:/mmview/` 再读。
- ASR 认错同音字（集金→就勤、MiraiMind→未来マインド）：只取时间。
