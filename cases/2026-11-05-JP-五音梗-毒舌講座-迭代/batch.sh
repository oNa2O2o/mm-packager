# 用法：bash batch.sh <VER> [draft|final]   VER='' / _2 / _3 / _4 / _5（'' = 视频.mp4，输出后缀 _1）
# 改用到新工程时只需改 D 和 NAME。
VER="$1"; KIND="${2:-draft}"; FV="${VER:-_1}"
D="F:/钟海明/2026/2026年11月5日MM-JP-五音梗-毒舌講座-迭代"; NAME="MM-JP-五音梗-毒舌講座-迭代"
SK="F:/BaiduSyncdisk/PI Agnet/.agents/skills/mm-packager"; M="$SK/modules/app-ui/appui.py"
cd "$D" || exit 1
[ -f "素材/视频${VER}_1080.mp4" ] || ffmpeg -nostdin -y -v error -i "素材/视频${VER}.mp4" -vf "scale=1080:1920:flags=lanczos,unsharp=5:5:0.6" -c:v libx264 -crf 16 -preset slow -c:a aac -b:a 192k "素材/视频${VER}_1080.mp4"
mkdir -p "工程素材/抽帧${FV}"; [ -f "工程素材/抽帧${FV}/0286.jpg" ] || ffmpeg -nostdin -y -v error -i "素材/视频${VER}_1080.mp4" -vf fps=24 -q:v 2 "工程素材/抽帧${FV}/%04d.jpg"
# 产品 UI 配置按版本隔离：抽帧路径换成本版
cd 包装素材_产品UI && VER="$VER" python - <<'PY'
import json, os, re
FV = os.environ['VER'] or '_1'
for n in ('swipe', 'chat'):
    s = open(n + '.json', encoding='utf-8').read(); s = re.sub(r'工程素材/抽帧[^/]*/', f'工程素材/抽帧{FV}/', s)
    open(f'{n}{FV}.json', 'w', encoding='utf-8').write(s)
PY
python "$M" render --config "swipe${FV}.json" --out "产品UI-划卡_v2${VER}.mp4" >/dev/null 2>&1
python "$M" render --config "chat${FV}.json" --out "产品UI-聊天_v2${VER}.mp4" >/dev/null 2>&1
# 图层 → timeline → 出片
cd ../包装素材v1/脚本 && VER="$VER" PYTHONIOENCODING=utf-8 python gen.py 2>&1 | tail -1 && VER="$VER" node to_timeline.mjs 2>&1 | tail -1 || exit 1
TL="$D/timeline${VER}.json"; mkdir -p "$D/导出"
if [ "$KIND" = final ]; then
  mkdir -p "$D/成品"; python "$SK/scripts/render.py" "$TL" --out "$D/成品/${NAME}_视频${FV}.mp4" && echo "FINAL 成品/${NAME}_视频${FV}.mp4"
else
  N=1; while [ -f "$D/导出/${NAME}_视频${FV}_校对预览_v$N.mp4" ]; do N=$((N+1)); done
  python "$SK/scripts/render.py" "$TL" --draft --out "$D/导出/${NAME}_视频${FV}_校对预览_v$N.mp4" && echo "OUT v$N"
fi
