# 修复复审记录（评审后一轮，2026-09-15）

单版评审发现 P0 共 9 处、P1 若干。按「仅 P0 触发一轮修复」执行，结果如下。
单版结论（verdicts/*.md）描述的是**修复前**状态；本文件是修复后的对账单。

## 已修复的 P0

| 版本 | 问题（评审员发现） | 修复 |
|---|---|---|
| A | AI 异常无兜底，失败占位卡可被采纳（app.py on_thinking） | collect_text 返回空即 snackbar 提示并返回，不再出卡（a_today_hub/app.py on_thinking） |
| B | `e`/`s`/`d` 三键在 README/命令文档承诺但无处理器 | on_key 补齐：e=重命名第一条未完成计划项、s=选中行动→进行中、d=完成（b_keyboard_inbox/app.py on_key） |
| B | 无焦点守卫：输入框里打 j/k/1/2/3 会误操作想法 | capture/worklog 挂 on_focus/on_blur，typing=True 时键盘流让路（同文件 _set_typing） |
| C | 「放弃/顺延」永久删项无撤销 | save_step3 改为整批可撤销（undo_snackbar 恢复到昨天），carry_items 返回被移除原文（c_review_wizard/app.py） |
| C | carry_texts 取"今天前 N 项"与实际顺延项可能错位 | 改为取 carry_items 实际移除的原文（同文件），smoke 断言同步 |
| D | 画布固定 560px 无滚动，≥7 个项目不可达 | 画布包进滚动容器并随窗口伸缩（d_structure_canvas/app.py build） |
| D | 拖拽无上界可把卡片拖丢，找回手段「适应窗口」又清空布局 | 拖拽坐标钳制在窗口可视区内（on_pan），卡片不可能丢出画布 |
| E | 通知卡写「可撤销」却无按钮，撤销只活在 6 秒 snackbar | 自动归档信息卡自带常驻「撤销这次自动归档」按钮（e_ai_concierge/app.py add_info_card/handle_watched_file） |
| E | AI 失败出「(AI 无返回)」占位卡且可采纳写盘 | 四处（计划建议/Check/周复盘/思考方式）失败一律不出卡，snackbar 提示降级；采纳后卡片离场防重复写盘（adopt） |

## 一并修掉的 P1

- E：目标下拉重复/漏项（build_target_options 每项目循环里插计划项）
- E：AI 生成前无进行中反馈（统一加「AI 生成中…」snackbar）
- B：命令文档与实际键位不一致（e/s/d 现已兑现，文档无需改）

## 评审员指出、本轮**不**修（记录为合并回正式版时的设计输入）

- C：向导每次启动重跑（无「今天已收尾过」记忆）
- C：AI 同步阻塞（E/A 同理；fake 端无感，真实端点需改异步任务）
- D：停滞红色劫持状态色语义；卡片无停滞天数（抽屉里有）
- B：改行动状态仍需先用鼠标点选标题（键盘选中行动未实现）

## 复验

- 5 个 smoke 全部 PASS；workbench 149 用例全绿
- E 重新截图（含常驻撤销按钮的自动归档卡）：review/screenshots/e_ai_concierge.png
