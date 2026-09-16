# B · 键盘流 + 收件箱零（Keyboard Inbox）

一句话：手不离键盘把想法清空，零 AI，验证"确定性操作会不会更快"。

- 运行：`python -m prototypes.b_keyboard_inbox.app --vault prototypes/ux-2026-09/demo_vault`
- 冒烟：`python -m prototypes.b_keyboard_inbox.smoke`
- 键位：`c` 捕获 · `j/k` 选择 · `1` 保留 · `2` 归档 · `3` 转今日计划 · `e` 重命名计划项 · `s/d` 行动直改状态 · `Ctrl+K` 命令面板（空查询=完整命令文档）。
- 交互哲学：Superhuman/Tana 的 touch-once 处理队列；一切列表有确定排序（待处理置顶、未完成置顶）；行动状态直接切换（`set_action_status`），不经 AI 提案。
