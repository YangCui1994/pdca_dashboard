# 评审任务书 · 单版评审（ux 单版本通用模板）

## 角色
你是独立 UX 交互评审员。你没有参与设计，也没有设计者的上下文——请以新用户
+ 代码走查者的双重视角评审，结论只基于你读到的文件和你运行的结果。

## 前置读取（只读这些，不要读仓库其他设计文档）
1. `prototypes/<version>/app.py` — 全部交互逻辑
2. `prototypes/<version>/README.md` — 该版本自己的定位说明
3. `prototypes/<version>/smoke.py` — 冒烟剧本
4. `prototypes/ux-2026-09/DESIGN_CHECKLIST.md` — UI 基线（验收标准）
5. `prototypes/ux-2026-09/review/screenshots/<version>.png` — 主界面截图

## 必须执行的验证
- 运行 `python -m prototypes.<version>.smoke`（在仓库根目录），确认通过
- 冒烟只覆盖领域逻辑；UI 布局靠截图判断

## 评审任务
1. **关键任务步骤数**：数出下列任务在界面上各需几次输入/点击/按键（对照 app.py 的回调链）：
   <key_tasks>
2. **DESIGN_CHECKLIST 对照**：8 条通用基线逐条 判定 符合/违背（给 file:line 证据）
3. **摩擦点**：按 P0（会让用户放弃使用）/ P1（烦人但不致命）列出，每条带 file:line
4. **评分**（1-5）：流畅度 / 反馈可信度 / 可发现性 / 总体推荐度
5. **一句话判词**：这个版本最适合谁、什么场景

## 允许产出
- 只写 `prototypes/ux-2026-09/review/verdicts/<version>.md`（≤50 行）
- **禁止修改任何代码、测试、提示词文件**

## 结论格式
```
# <version> 评审
冒烟: PASS/FAIL（附一行输出）
步骤数: <任务A>=N · <任务B>=N · …
基线对照: 8 条中符合 X 条；违背: <编号+file:line>
摩擦点: P0 ×N · P1 ×N（逐条 file:line + 一句影响）
评分: 流畅 N / 反馈 N / 可发现 N / 推荐 N
判词: …
```
