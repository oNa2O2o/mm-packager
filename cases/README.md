# 案例

- `2026-11-05-*` 起的案例是 mm-packager（timeline.json + render.py）写法，脚本可直接改用。
- 更早的案例来自编辑器时代（mm-workbench-v5）：`patch*.mjs` 是往编辑器 API 写工程的脚本，**不能再直接运行**。只参考其中的 `gen.py`（图层设计）、音效合成、人脸跟踪/抠图等做法；写工程那步改成生成 timeline.json（格式见 `reference/layers.md`，改写示例见毒舌講座迭代 `to_timeline.mjs`）。
- 数值、文案只作参考，不照搬。
