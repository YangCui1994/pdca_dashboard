# E · AI 主控台（AI Concierge）

一句话：ymos 的「阶段 → 提示词文件 → 人工确认」编排产品化——AI 产草稿卡，你决定落不落盘。

- 运行：`python -m prototypes.e_ai_concierge.app --vault prototypes/ux-2026-09/demo_vault --watch-dir prototypes/ux-2026-09/watch_inbox`
- 冒烟：`python -m prototypes.e_ai_concierge.smoke`
- 阶段草稿卡：今日计划建议 / Check 引导 / 本周复盘，每张卡【采纳 / 改后采纳 / 忽略】。
- 思考方式下拉：目标（想法/项目/计划）× 模式（brainstorm/grill_me/six_hats/premortem，注册表自动发现）→ 草稿卡。
- 文件监听：`watch_inbox/` 来新 `.md/.txt` → `file_route` 判定 → 高置信自动追加项目进度（通知卡带一键撤销）；低置信出草稿卡；无关留痕。
- 唯一的自动写盘分支就是上面的高置信路由（可撤销），其余一切落盘必经人工确认。
