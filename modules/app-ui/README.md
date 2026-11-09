# 产品 UI 模板（app-ui）· 剧情后的「软件功能展示」

用在**剧情结束之后**，把观众带进产品界面（投放原则 §0.5：转化承接照产品真实 UI 做）。1080×1920，30 fps，渲染出带音效的 mp4，作为 video clip + 同源 audio 放进 timeline.json。

| 模板 | 内容 | 状态 |
|---|---|---|
| `swipe` 划卡到角色详情 | 首页角色卡横滑 3 张 → 停在本片角色上 → 点开卡片 → 卡片缩到左上角，详情页弹出（名字、标签、キャラ情報 面板）→ 点「チャットに進む」 | **2026-11-02 用户验收**，照 `reference/产品录屏_划卡到详情.mp4` 做 |
| `chat` 聊天界面 | 本片角色的聊天页，消息逐条弹出（文字 / 图片 / 语音条 / 输入中），可以模拟用户在输入框打字并发送 | 第一版，用户没单独验收；用之前先出静帧给用户看 |

不包含片尾（Logo、CTA、商店标）。片尾另外用 `jp-endcard`、模板 `end/liquid` 或自己做，接在这段后面。

## 用法
```bash
M="$SK/modules/app-ui/appui.py"
python $M stills --config cfg.json --out <工程>/包装素材_产品UI/静帧 --times 0.4,1.3,3.4,4.0,5.5   # 先看静帧
python $M render --config cfg.json --out <工程>/包装素材_产品UI/预览.mp4                         # 单独出片
```
- 渲染出的 mp4 放 `<工程>/包装素材_产品UI/`，在 timeline 里 `{"type":"video","src":…,"start":T}` + 同 src 的 audio 条目。
- 配置里的图片一律写**绝对路径**。工程配置和卡片截图都放在**工程目录**里（`包装素材_产品UI/`），不要放进 skill。
- 例子：`examples/swipe_floze.json`、`examples/chat_floze.json`（floze迭代2 的测试配置，路径指向那个工程）。

## swipe 配置
```json
{"template":"swipe",
 "cards":[{"image":"…/卡1_女仆.jpg","focusY":0.35},{"image":"…/卡2_二争一.jpg"},{"image":"…/卡3_雪女.jpg"}],
 "hero":{"image":"…/抽帧/0300.jpg","focusY":0.35,"name":"蓮","tags":[],"intro":"","gallery":["…/0444.jpg","…/0200.jpg"]}}
```
- `cards`：前面划走的卡。**用户定的做法：用其他已上线素材里的角色**（2026-11-02 用的是女仆、二争一、雪女，从各自工程的源视频截一帧好看的全身或半身画面）。卡上只显示图，`name/tags/intro` 有来源才填。
- `hero`：最后停住的卡，**用当前工程的内容**（本片角色抽帧）。`name` 写全量文案里的角色名；`tags/intro` 只能来自文案或用户，没有就留空，那样详情页的「紹介」段就不画；`gallery` 是详情页「キャラクター」里的小图（最多 3 张，第 1 张固定是 hero.image）。
- 节奏参数（单位秒，括号里是默认值）：`startAt`(.5)、`firstSwipe`(.8)、`accel`(.78，每张划得更快)、`minSwipe`(.38)、`swipeGap`(.12)、`heroHold`(.8，停多久再点)、`profileHold`(2.2，详情页停多久再点チャットに進む)、`tapChat`(true，设 false 就不点)、`tail`(.7)。默认 3 张卡总长约 7.2 s。 可选 `scrollUp`(0，详情页打开后整页上滑的像素，带手指上划；2026-11-05 误入的少女用 450 展示简介)、`scrollAt`(.5，详情页打开后多久开始滑，滑 .7 s)。
- `ui`：覆盖产品按钮/标签文字，默认值照产品录屏（JP）：`chat:"チャット"`、`chatGo:"チャットに進む"`、`tabs:["キャラ情報","シナリオ","アルバム","グループ"]`、`intro:"紹介"`、`chara:"キャラクター"`、`nav:["ホーム","検索","","チャット","マイ"]`。**这些是产品 UI 原文，可以直接用；做 KR/EN 素材时要换成该语言版产品里的实际文字（向用户要截图或录屏），不要自己翻译。**

## chat 配置
```json
{"template":"chat","bg":{"image":"…","focusY":0.4,"dim":0.15},"name":"蓮","status":"","avatar":{"image":"…","focusY":0.3},
 "placeholder":"","chips":[],"fontSize":56,
 "messages":[{"t":0.6,"from":"char","text":"一年ぶりだよね"},
             {"t":1.6,"from":"char","type":"image","image":"…/0444.jpg","w":520,"h":700},
             {"t":2.9,"from":"char","text":"…","typing":0.6,"voice":6},
             {"t":4.0,"from":"user","text":"…","typeDur":1.2},
             {"t":6.2,"from":"char","text":"","typing":1.4}],"tail":0.4,"duration":6.0}
```
- `t` 是消息出现的时间。`typing` 表示消息出现前先显示多少秒「…」；`text` 为空、只写 `typing` 时，就一直停在「输入中」。`from:"user"` 配 `typeDur`，会先在输入框里逐字打出来，再点发送。
- 消息文字只能来自全量文案。`status/placeholder/chips` 没有来源就留空。

## 渲染细节与坑
- **抗锯齿**：内部按 `ss` 倍绘制（默认 2）再缩小。**图片的圆角不能用 `clip()` 切**，canvas 的 clip 边缘不做平滑，2 倍绘制也消不掉锯齿（2026-11-02 用户指出），要用引擎里的 `masked(pathFn, drawFn)`：先把图画到单独一层，再用带平滑的 `fill` 做 destination-in 扣出形状。新加的圆角图片都要走这个函数。
- 按钮样式照产品，**改的时候不要偏离产品**（用户：「UI 可以精简，但是按钮相关的都必须和产品大差不大」）：「チャット」「チャットに進む」都是青 #74E8D0 → 蓝 #70B4FF → 淡紫 #BBA0FF 的渐变胶囊，配深色字。
- 音效复用 `jp-endcard/media/audio`：点击用 sfx_click_1，打开详情用 sfx_toggle_2，消息用 sfx_message_1；划卡声是用粉噪合成的。交付时写明「音效需要你听一下」。
- 字体、Logo、商店标复用 `jp-endcard/engine/assets`，渲染用的 Chrome 路径写死在 `appui.py` 的 `CHROME`。
