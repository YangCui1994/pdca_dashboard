# A · 今日中枢（Today Hub）

一句话：单页做完一天的事——捕获、计划、记录、想法处理都不切页。

- 运行：`python -m prototypes.a_today_hub.app --vault prototypes/ux-2026-09/demo_vault`
- 冒烟：`python -m prototypes.a_today_hub.smoke`
- 交互哲学：Things 3 的 Today 即家 + Todoist 快速捕获路由（`!`→计划、`#项目`→归属计划、纯文字→想法）+ 昨日未完成一键顺延（可整体撤销）+ 想法 touch-once（入今日/保留/归档/点名思考方式）。
- AI：仅一处可选（想法行的思考方式下拉，fake provider 离线可跑）。
- 关键代码：`app.py` 的 `route_capture`（纯函数，冒烟覆盖）。
