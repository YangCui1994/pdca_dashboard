# D · 结构画布（Structure Canvas）

一句话：archify「可交互结构图」思路的原生 Flet 实现——项目即卡片，空间即结构。

- 运行：`python -m prototypes.d_structure_canvas.app --vault prototypes/ux-2026-09/demo_vault`
- 冒烟：`python -m prototypes.d_structure_canvas.smoke`
- 交互：项目卡可拖拽（布局持久化到 `prototypes/ux-2026-09/canvas_layout.json`）；「适应窗口」一键回网格；点卡片开底部抽屉看大纲与行动色块；点色块循环切换状态（不经 AI）；停滞 15 天的行动红框+真实停滞天数。
- 卡片元信息（最近活跃/进行中/停滞数）全部来自活动流，宁空勿假。
- 零 AI；原型阶段刻意不做 minimap。
