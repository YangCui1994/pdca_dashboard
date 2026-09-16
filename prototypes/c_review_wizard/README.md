# C · 引导复盘（Review Wizard）

一句话：打开先收尾昨天，把 PDCA 的 C/A 补成闭环，再看今天。

- 运行：`python -m prototypes.c_review_wizard.app --vault prototypes/ux-2026-09/demo_vault`
- 冒烟：`python -m prototypes.c_review_wizard.smoke`
- 向导四步（每步只问一件事 + 顶部进度点）：①勾昨日完成 → ②AI 引导写 Check（可改可跳）→ ③未完成项逐条「今日再做/放弃」→ ④写 Act 并生成今日计划。
- Check/Act 落 DayRecord 并同步 `days/<日期>.md` 的 `## Check` / `## Act` 段（workbench 存储层新增能力）。
- 向导后：`←`/`→` 切换日期，任何一天的 Check/Act 都能回看补写（修复正式版 Today 写死当天的问题）；另有「生成本周复盘」AI 草稿。
