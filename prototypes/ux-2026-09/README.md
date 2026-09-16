# UX 改版实验（2026-09）：五个可对比的交互原型

针对「v2 Flet 正式版使用起来不顺手」，做五个各主打一种交互哲学的可运行
原型，共用一份确定性演示数据，跑起来对比手感，选定方向后合并回正式版。
**不碰正式版、不碰 v1、不碰真实 `data-issue-vault/`。**

## 快速开始

```bash
# 0) 生成演示数据（已存在则跳过；--reseed 重置）
python -m prototypes.uxbase.seed_demo --reseed

# 1) 五个版本（都是 fake provider，离线可跑）
python -m prototypes.a_today_hub.app       --vault prototypes/ux-2026-09/demo_vault
python -m prototypes.b_keyboard_inbox.app  --vault prototypes/ux-2026-09/demo_vault
python -m prototypes.c_review_wizard.app   --vault prototypes/ux-2026-09/demo_vault
python -m prototypes.d_structure_canvas.app --vault prototypes/ux-2026-09/demo_vault
python -m prototypes.e_ai_concierge.app    --vault prototypes/ux-2026-09/demo_vault --watch-dir prototypes/ux-2026-09/watch_inbox

# 2) 冒烟（headless，断言落盘）
python -m prototypes.a_today_hub.smoke   # 其余同理
```

真实 AI：任一原型加 `--provider openai --ai-base-url … --ai-model …`（或环境变量
`WORKBENCH_AI_*`）。不配就是 fake，输出确定性中文草稿。

## 五个版本与 5 分钟体验剧本

| 版本 | 一句话 | 剧本 |
|---|---|---|
| A 今日中枢 | 单页做完一天的事 | 在捕获条依次输「!给运营同步口径」「#星图演示库 跟进差异」「把异常标注做成栏目」→ 看三种落点 → 勾一条计划 → 点「顺延到今天」→ 右侧想法行点「入今日」→ 想法行最后一个按钮点名「拷问假设」 |
| B 键盘流 | 手不离键盘清空收件箱，零 AI | `c` 聚焦捕获回车 → `j/k` 移动 → `3` 转计划 → `1` 保留 → `Ctrl+K` 看命令文档 → 右侧行动点 `s`/`d` 直改状态 |
| C 引导复盘 | 打开先收尾昨天，补齐 C/A | 跟着向导走完四步（Check 可让 AI 起草）→ 完成后 `←` 切到昨天看 md 镜像的 Check/Act → 点「生成本周复盘」 |
| D 结构画布 | 项目即卡片，空间即结构，零 AI | 拖两张卡片 → 重启应用看布局保留 → 点卡片看大纲抽屉 → 点行动色块循环状态 → 看停滞红框与真实停滞天数 |
| E AI 主控台 | 阶段草稿卡时间流 + 文件监听 | 点「今日计划建议」→【采纳】→ 目标×思考方式下拉选一组点「运行」→ 往 `watch_inbox/` 丢一个 md 文件，5 秒内看路由卡（高置信自动归档可撤销；文件里含「[低置信]」则出确认卡） |

对比决策清单（勾完就知道选哪个）：
- 捕获速度优先 → A；处理积压优先 → B；复盘闭环优先 → C；全局视野优先 → D；AI 协作优先 → E
- 最终形态大概率是「A 的骨架 + B 的键位 + C 的向导 + E 的草稿卡」，本 README 记录你的选择即可

## 借鉴来源

- Todoist Quick Add（自然语言路由捕获）、Tana（收件箱 touch-once、Quick Add 弹窗）
- Things 3（Today 即家、未完成顺延）、Obsidian（就地编辑、自动保存）
- 日志类应用（Day One 等）的引导式复盘
- [ymos（本地 05_DS_YMOS）]：`Agents/` 角色卡 + `Brain/references/pN-*.md` 按阶段编号的提示词、提示词头自声明前置读取/写回边界、Human 确认原则——本实验的 `prompts/` 双轴结构直接照此设计
- [archify]（`docs/ARCHIFY.md`）：「可交互结构图」的思路被 D 版产品化；archify 本体只用于生成 `docs/architecture.html`，不进产品运行时

## 关键决策与理由（防遗忘）

1. **原型复用 workbench 的 service/storage**：原型验证过的交互逻辑合并回正式版时零翻译成本；服务层为此新增了三个带测试的小方法（见下）。
2. **E 版高置信文件路由自动追加进度**：这是对「AI 落盘必经人工确认」红线的唯一偏离，因为用户明确要"自动判断是否添加"；补偿措施是通知卡一键撤销 + 活动流留痕 + 低置信一律回人工确认。
3. **B/D 刻意零 AI**：AI 强度做成梯度（A=1 处、B=0、C=2、D=0、E=全阶段），对比"AI 多 vs 少"的手感，而不是五个版本都堆 AI。
4. **archify 不进运行时**：它是 Node 工具链，塞进零依赖 Python/Flet 产品违反约束；产品内结构可视化由 D 版原生实现。
5. **watcher 用 stdlib 轮询**（5 秒，mtime+size 去重）：不引入 watchdog；PDF/docx 解析会引入依赖，列 backlog。
6. **放弃「时间流日志」方向**（Logseq 式万物归一条流）：与 A 的今日中枢重叠度高，五个版本已覆盖其核心价值（捕获即记录）。

## workbench 服务层新增（带测试，合并回正式版的前提）

- `WorkspaceService.set_action_status(project_id, action_id, status)`：不经 AI 的直接状态切换
- `WorkspaceService.set_day_check/set_day_act` + `DayRecord.check_note/act_note`：PDCA 闭环字段，同步 `days/<日期>.md` 的 `## Check`/`## Act` 段
- `WorkspaceService.append_project_progress/remove_project_progress` + `Project.progress`：项目进度审计与撤销

## 验证结果（2026-09-15）

- `python -m unittest discover -s workbench/tests`：**149 个用例全绿**（含 service/storage 扩展、prompt loader、watcher/router 新用例），连跑 3 遍稳定
- 5 个冒烟脚本全绿（路由/勾选/顺延/流转/思考采纳/向导四步/布局持久化/文件路由三分类+撤销）
- 5 个原型逐个真实启动（fake provider），截图见 `review/screenshots/`——界面元素、语义色、停滞红框、草稿卡均正常渲染

## 评审产物

- `review/briefs/`：评审任务书（前置读取/允许产出边界，ymos 合同式写法）
- `review/screenshots/`：五个版本的主界面自截（`page.take_screenshot`，非 OS 截屏）
- `review/verdicts/`：单版评审 ×5 + 横向对比 ×1 的结论（不共享上下文的子代理产出）
