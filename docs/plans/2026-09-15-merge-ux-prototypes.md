# workbench 合并执行计划（UX 原型 → 正式版 v2）· 完整版

状态：**已完成（2026-09-16）**。五阶段全部落地,三道门+视觉 reviewer 通过;执行记录与恢复线索保留在本文,完成状态另见 docs/NEXT_PLAN.md 的"UX Prototype Merge — LANDED"节。
自包含——新会话仅凭本文+仓库现状即可恢复执行。执行口令："按 docs/plans/2026-09-15-merge-ux-prototypes.md 执行合并"。

## 0. 执行方式

分 5 个阶段（见 §9），每阶段结束跑全量测试。**发布前三道门强制执行（§7）**。

## 1. 背景与已定决策

- 正式版 workbench/（Flet 0.86.5）目标形态改为**网页模式**（view=WEB_BROWSER）用于公司内网部署：main.py 加 `--ui web|desktop`（默认 web）+ `--host/--port`；无认证仅限内网；多会话并发写触发 StorageConflict，首版按"单人使用多端查看"定位
- 五个原型（prototypes/，网页模式 8551-8557）已做独立评审，排名 **A > C > B > E > D**
- 合并方向（已定）：**A 今日中枢做今天页骨架 + C 四步收尾向导 + E 草稿卡/思考方式库/文件监听 + D 改造为项目页 master-detail**
- **B 键位层不合入（2026-09-15 晚已定）**：不用 vim 式 jk 选择；想法列表仅保留**上下方向键移动选择**这一条轻量便利，其余全鼠标操作；B 的其余产出（排序规则、touch-once 队列）已由 A 覆盖
- **D 试用反馈（同晚已定）**：弹窗/自由画布否决 → 项目页改为**左 1/4 项目列表（纵向可滚动紧凑卡：名称+元信息+停滞红标）+ 右 3/4 大详情区（大纲+行动色块直改）**
- **UI 风格（2026-09-16 更新，覆盖原紫色主题决策）**：字体和颜色沿用 **entp-manual** 项目风格（https://github.com/TANGuoGUO/entp-manual ，已克隆 `refs/entp-manual/`，commit e03393e）。主色蓝 `#316BEE`（soft `#EEF3FF`）、INK `#171A21`、MUTED `#737986`、边框 `#E7E9EE`、SURFACE `#FFFFFF`、SIDEBAR `#F7F8FB`、CANVAS `#FBFCFE`、GREEN `#37A46A`/`#EAF7EF`、AMBER `#B87818`/`#FFF6DF`、RED `#E45959`；全局字体 Microsoft YaHei UI、等宽 Consolas；仅浅色模式。完整对照表：`refs/SOURCES.md`。原型橙色弃用
- 红线：AI 只产草稿、落盘必经人工确认（唯一例外 file_route 高置信自动追加必须可撤销）；不动 v1（app/）；不加第三方依赖；真实 data-issue-vault 默认不触碰

## 2. 服务层已就绪（已合入+测试，149 全绿基线）

set_action_status / DayRecord.check_note+act_note（+days/<日期>.md 镜像）/ append_project_progress+remove_project_progress

## 3. 新模块（全部带测试）

- `services/capture_routing.py`：route_capture（`!`→计划、`#项目`→归属、纯文字→想法）+ parse_plan_lines
- `services/wrapup.py`：apply_marks/carry_items/act_draft/plan_summary
- `services/prompt_library.py`：双轴注册表（stages×5+thinking×4，扔进 md 即新增），正式家 `workbench/prompts/`
- `runtime/text_runtime.py`：FakePromptRuntime/OpenAITextRuntime
- `services/file_watcher.py`+`file_routing.py`：mtime+size 去重；`--watch-dir` 可选
- `components/feedback.py`：snackbar/可撤销/空态（THEME 配色）
- `prototypes/uxbase` 改为上述模块的 re-export 壳（原型零改动；workbench/tests 的 test_prompt_loader/test_watcher_router 改 import）

## 4. 今天页 → TodayHub（views/today.py 重构）

- 智能捕获条（左栏顶部常驻）：回车路由落点，清空+焦点回归+snackbar
- 顺延条：昨日未完成 N 项→[顺延到今天]（整批可撤销）+[昨日收尾向导]；昨日 check/act 非空显示"已收尾 ✓"
- 计划卡保留勾选/双击改名/@项目徽章/添加行；CLOSE 删除改可撤销
- 想法行：[入今日][保留][归档][思考方式▾]（全鼠标；上下方向键可移动选择高亮）；右栏顺序契约 [待整理想法, 整理上下文] 保持
- 「生成整理建议」死按钮（today.py:294-297）接线→计划建议草稿卡（三键：采纳/改后采纳/忽略，AI 失败不出卡）；加 Check 引导、周复盘入口；草稿卡右栏底部
- C 向导 `components/wrapup_wizard.py`：AlertDialog 四步+进度点；向导后回今天页
- 工作记录保留 build_editable_markdown；AI 审查抽屉/提案流程不动；today 页内变更局部刷新（全局 render() 不动）

## 5. 项目页 → master-detail（D 新形态）

- project_overview：左 1/4 项目紧凑卡列表（纵向滚动、点击选中高亮、停滞红标+真实天数）+ 右 3/4 详情区（目标/阶段/里程碑、大纲、行动色块点按循环状态、停滞天数）；自由画布不进正式版
- P0 顺手修：总览「今日任务」勾选接 service（:193-200 回弹）；node_detail 假数据改真实（:179-187）；navigation 隐藏死入口设置/回收站（:24-27）

## 6. AI 异步

所有 runtime 调用异步：优先 page.run_thread（先探测 0.86 可用性），否则 threading.Thread+page.update；真实端点不得冻结界面

## 7. 发布前三道门（强制，违反=事故）

1. **构建自检**：FakePage 只构建不启动（已实证能抓 Row 参数名/detail_panel 顺序类错误）
2. **code reviewer 静态审查**：清单=flet 0.86 踩坑全集：ft.border.all→ft.Border.all、ft.padding.only→ft.Padding.only、无 ft.alignment.center、TextSpan 走 style、无 page.open→show_dialog、Stack 定位在直接子控件、enable_screenshots 在 page.add 前、import 完整性（曾漏 os）、构建顺序 AttributeError
3. **桌面自截门**：UX_SHOT 自截干净落盘、日志无 Traceback，才允许网页模式开给用户

网页僵尸防护：释放端口必须按 netstat -ano 的 PID 杀（flet.exe 子服务器在父死后仍存活），重启前确认端口 LISTEN 已消失

## 8. 契约与测试

- 改约：test_today_has_no_local_capture_input（test_ui_contract.py:356）→"恰 1 个常驻捕获框"
- 新契约：捕获路由三落点、顺延条、思考方式菜单、草稿卡三键、向导四步、项目页 master-detail
- 树遍历契约易碎（控件类型+行序敏感）：先跑基线逐条对账，不静默删测试
- 全量 `python -m unittest discover -s workbench/tests` 全绿（149+新增）；prototypes 五个 smoke 继续绿

## 9. 执行顺序（每步全量测试）

①服务层+新模块+prompts 迁移（uxbase 改壳）→ ②今天页 TodayHub → ③项目页 master-detail+P0 → ④AI 异步+--ui web → ⑤文档（README 加 --watch-dir/--ui、NEXT_PLAN 状态、DESIGN_CHECKLIST 勾 P0）

## 10. 现状与恢复线索

- 原型运行：`python -m prototypes.{a_today_hub,…}.app --vault prototypes/ux-2026-09/demo_vault [--port N]`（默认网页）；冒烟 `python -m prototypes.<名>.smoke`
- 评审产物：`prototypes/ux-2026-09/review/`（verdicts 排名 A>C>B>E>D、REPAIRS.md 9 P0 修复对账、screenshots、briefs）
- UI 风格基准：`refs/entp-manual/`（flet_app.py:80-93 色板、:525-530 主题）+ `refs/SOURCES.md` 对照表
- archify：docs/architecture.html（visual-check 已过）；flet 0.86 踩坑清单也在 DESIGN_CHECKLIST
- 开放问题（执行中再问）：捕获条常驻形态、Ctrl+K 是否要、"已收尾"判定口径、watch 默认开关、思考方式下拉位置

## 不做

不动 v1；不改数据布局；不加第三方依赖；真实 vault 默认不触；**vim 式 jk/数字键选择不合入**；Ctrl+K 与行动 s/d 键列 backlog；PDF/docx 路由列 backlog
