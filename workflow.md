# 工作流

```bash
SK="F:/BaiduSyncdisk/PI Agnet/.agents/skills/mm-packager"
RES="Z:/创新事业部/AIGC项目视频组/mm-packager资源"
P="<工程目录>"; COPY="$P/全量文案.md"
export PYTHONIOENCODING=utf-8      # Windows 控制台是 GBK
```
目录约定：
```
<工程>/素材/                 源视频（多版本 视频_1.mp4、视频_2.mp4…）
<工程>/工程素材/抽帧_<版本>/   每版独立抽帧
<工程>/包装素材vN/           图层 PNG；audio/；脚本/{gen.py,to_timeline.*,batch.sh}
<工程>/包装素材_产品UI/        swipe/chat 配置与渲染出的 mp4
<工程>/timeline<版本>.json
<工程>/导出/  <工程>/成品/
```

## 1. 拆片
- 抽帧：`ffmpeg -i 视频 -vf fps=24 工程素材/抽帧_<版本>/%04d.jpg`；联系表拼一张 read（先写笔记）。
- 480p 等低分辨率：`scale=1080:1920:flags=lanczos,unsharp=5:5:0.6` 放大一份 `<名>_1080.mp4` 用。
- 时间：`python $SK/scripts/asr.py 视频 --segments ... --prompt "该幕文案"`，得到逐词时间；对照能量确认（-35 dB）。

## 2. 定方案（先给用户）
时间表：标题/钩子、字幕、选项、承接（划卡/聊天）、口播、片尾、BGM/音效。对照 standards §0。屏幕文字逐条注明来自全量文案哪句；日语附中文。
- 转化文案先讲产品再讲剧情；口播优先从 shortdrama-copy 的 `references/投放高效文案.md`（看板达标文案）选。
- 划卡其他卡：`library/cards.md` 取，卡面图在 `$RES/library/cards/`。

## 3. 图层（gen.py）
1080×1920 透明整画布 PNG，元素画在最终位置；动画用 timeline 关键帧。逐帧动画输出 `name_%03d.png` 用 sequence clip。字体从 `$RES/fonts/` 读。重新生成换新文件名不是必须（render 不去重），但旧图要清掉。格式见 `reference/layers.md`。

## 4. 承接 / 片尾
- 产品 UI：写 `包装素材_产品UI/swipe.json`、`chat.json` → `python $SK/modules/app-ui/appui.py stills --config ...` 看静帧 → `render --config ... --out 产品UI-划卡_vN.mp4`，作为 video clip 放进 timeline（自带音效，单独加 audio）。
- JP 尾板（用户选了才加）：`python $SK/modules/jp-endcard/endcard.py render ...`，同样作为 video clip 接在末尾。
- 承接转场：正片最后 0.6 s 推近（scale 关键帧）+ 闪白图层，再切 UI。

## 5. 声音
- 原声：源视频作为 audio 条目（与 video clip 同 start/in/duration）。
- 口播：voice skill（ElevenLabs，原片有口播用同一音色）；atrim 去首尾静音，必要时 atempo 1.05–1.15。口播必配字幕+底板。
- BGM：music skill 每次新生成，剧情/承接分开；ElevenLabs CLI `--json` 写 composition plan（每段 ≥3000 ms）；环境变量 Key 无 music 权限时 `env -u ELEVENLABS_API_KEY` 走 CLI 登录。demucs 测人声 < -45 dB。人声/口播段 BGM 压低（duck .1 左右），无人声段 .25–.3。
- 音效：`$RES/sfx/`。

## 6. 出片
```bash
python $SK/scripts/render.py $P/timeline.json --still 1.0 4.2 9.5 13 20   # 静帧，拼图 read
python $SK/scripts/render.py $P/timeline.json --draft                      # 540×960 预览，改名 _校对预览_vN.mp4
python $SK/scripts/render.py $P/timeline.json                              # 成片 1080×1920
```
自检：ffprobe 尺寸/时长/yuv420p/有音轨；`ffmpeg -af ebur128` 约 -18 LUFS、峰值 ≤ -1 dB；`blackdetect` 无意外黑屏；关键帧拼图目视（字幕=文案、卡片字段齐全不出界）。打开预览给用户。

## 7. 交付
验收后：成片复制到 `成品/<目录名去日期>.mp4`（多版本 `_视频N`），打开 `成品/`。然后：
- 存案例 `$SK/cases/<日期>-<地区>-<标题>/`：脚本 + README（类型、方案、用户修改过程、踩坑 3–5 行）。
- 本片角色卡追加到 `library/cards.md` 顶部（卡面图复制到 `$RES/library/cards/<日期>-<标题>.jpg`），文案追加到 `library/copy.md`。
- 用户新提的**通用**要求写进 SKILL 硬规则或 standards（注明日期）。

**无 BGM 版**：timeline 去掉 BGM 条目再出一份 `成品/<名>_无BGM版.mp4`。

## 8. 多版本（同台词换角色）
- 每版重做：抽帧（`抽帧_<版本>`）、ASR 时间、定格帧、卡面/hero/背景帧、错误人声检查。
- 沿用：设计、文案、口播、BGM、音效。
- 做法：gen.py 里 `TM = {版本: {时间…}}`，`VER=_2 python gen.py && VER=_2 node to_timeline.mjs && render`；`batch.sh <VER> [draft|final]` 一键。参考 `cases/2026-11-05-JP-五音梗-毒舌講座-迭代/`。
- 先做 1 个给用户确认，再批量。

## 排错
| 现象 | 处理 |
|---|---|
| faster-whisper 段错误 / CUDA 报错 | `asr.py` 自动转 CPU；仍不行 `--engine scribe` |
| 长视频 ASR 前段糊成一个词 | `--segments` 按幕切 + `--prompt` |
| 日文变细体 / 缺字 | 字体用 `$RES/fonts/` 里带假名的（NotoSansJP、MochiyPopOne…） |
| 混音爆音 | render 默认 alimiter .89；仍爆就降音效 volume |
| OpenCV 读不了中文路径 | `cv2.imdecode(np.fromfile(p,np.uint8),…)`；模型在 `$RES/models/` |
| ElevenLabs 音乐分段报错 | 每段 `duration_ms` ≥ 3000；`--prompt` 报 sections 缺失改 `--json` |
| Z: 盘读不到 | 确认网络盘映射，或 `MM_RES` 指向本地副本 |
