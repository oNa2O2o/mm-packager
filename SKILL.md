---
name: mm-packager
version: 2.0.1
description: 把一个视频 + 一份全量文案包装成 MM 投放成片（标题、字幕/气泡、选项定格、好感度、产品 UI 划卡/聊天承接、口播、片尾/JP 尾板、BGM/音效），不依赖编辑器：PIL 生成图层 → timeline.json → scripts/render.py 直接出校对预览/成片，验收后交付到素材目录的「成品」。支持多版本（同台词换角色）批量出片。用户说“包装这个视频”“MM 包装”“做 MM-KR/JP/EN/TC 包装”“AI包装”“重新设计包装”“迭代版本”“换角色同台词”“无BGM版”“加JP尾板”“接尾板”“划卡承接”“网感剪辑”“用 v5 编辑器包装/mm-workbench-v5”时使用（v5 已迁移到本 skill）。
---

# MM 包装（mm-packager）

不用编辑器。每条片子 = 工程目录里的脚本：`gen.py`（PIL 画图层）→ `to_timeline`（写 `timeline.json`）→ `render.py`（逐帧合成 + ffmpeg 混音出片）。

- 本 Skill `$SK` = `F:/BaiduSyncdisk/PI Agnet/.agents/skills/mm-packager`
- 共享资源 `$RES` = `Z:/创新事业部/AIGC项目视频组/mm-packager资源`（字体、音效、模型、JP 尾板素材、投放参考、卡面库；环境变量 `MM_RES` 可覆盖）
- 开工先跑 `python $SK/scripts/check_env.py`，缺什么自己装好（交付说明写一句装了什么）。

## 硬规则（用户定的）
**目录与交付**
1. **用户给的素材目录就是工程目录**，产物（素材、脚本、图层、timeline、导出）全放里面，不在别处建目录。用户没给才新建 `F:/钟海明/2026/YYYY年M月D日MM-<地区>-<标题>`。
2. **导出按版本号命名**：`导出/<目录名>_校对预览_vN.mp4`（`render.py --draft`）。验收合格 = 必须出成片（1080×1920 yuv420p）复制到 `<工程>/成品/`，用户忘了说也要做；旧版移 `归档/旧版成品vN/`。
3. **改完就给用户看**：每次修改后打开预览视频；只开图和视频，脚本/json 不开目录。

**内容**
4. **全量文案只读**：屏幕文字只来自全量文案；要加字/改字先向用户申请。用户给的中文先改成目标语言地道说法。
5. **不编台词**：无人声段不加字幕；ASR 只用来取时间（会幻听、认错同音字）。原声与文案不一致先问用户。
6. **画面不空、不黑**：任何时刻底层都有画面；定格帧不能是黑帧。
7. **正片切到产品 UI 要有承接转场**（例：推近手机 0.6 s + 闪白进首页），不能硬切。
8. **口播必须有字幕，字幕必须有底板**（半透明圆角底 + 描边），不能和背景糊在一起。
9. **BGM 每次新生成**，剧情段和承接段分开生成，强制纯音乐（demucs 测人声 < -45 dB）；不复用往期 BGM。
10. **划卡里每张卡都要有名字和简介**：其他角色卡优先从 `library/cards.md` 取（“用近 N 个素材的卡片” = 表里前 N 个素材）。
11. **多版本按版本隔离**：抽帧、卡面、背景帧、时间表按版本分目录/后缀；引用其他素材的画面从**原始素材**取，不从成片截。
12. **自己检查后再交付**：关键时刻静帧拼图 read 目视；声音只能看频谱/响度，交付时写“需要你听一下”。

**沟通**
13. 给用户看的方案、文案里日语/韩语全部附中文。用户给过的信息直接用，不再问。
14. 先报计划，用户确认再做。

## 流程（详见 workflow.md）
拆片（抽帧 + `scripts/asr.py` + 能量）→ 定方案（对照 `reference/standards.md` §0 投放原则）→ `gen.py` 出图层 → 承接（`modules/app-ui` 划卡/聊天）→ 口播（voice skill）、BGM（music skill）→ `timeline.json` → `render.py --still` 看版面 → `--draft` 校对预览 → 改 → 成片交付 → 存案例、更新 `library/`。

## 文件
| 文件 | 何时读 |
|---|---|
| `workflow.md` | 每次包装：步骤、多版本、交付、排错 |
| `reference/standards.md` | **§0 投放原则** + 审美标准 + 可选打法，每次包装前读 |
| `reference/layers.md` | timeline.json 格式、图层/关键帧/音频规则、环境坑 |
| `reference/投放参考/README.md` | 产品 UI、商店页参考，做承接/片尾前看 |
| `library/cards.md` / `library/copy.md` | 往期卡片库（名字/简介/标签/卡面路径）、往期包装文案；交付后追加本片 |
| `modules/app-ui/README.md` | 划卡 `swipe` / 聊天 `chat` 承接 |
| `modules/jp-endcard/README.md` | JP 尾板（17.3 s 3D 卡片 + 口播），JP 可选片尾，问用户再加 |
| `cases/` | 已验收案例（脚本可改用；数值/文案不照搬） |
| `scripts/render.py` | timeline → mp4 / 静帧 |
| `scripts/asr.py`、`check_env.py`、`figma_ref.py`、`store_ref.py`、`open_dir.ps1` | 逐词时间、环境自检、产品 UI 截图、商店页、开目录 |
