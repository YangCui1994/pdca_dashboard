# Personal Workbench v2 — 正式化计划调整（2026-08-31）

状态：已批准执行

调整对象：`docs/plans/2026-08-30-personal-workbench-v2-glm-execution.md` 第 12 节 P1–P8 backlog。
自 2026-08-31 起，正式化工作以本文档为准；原清单保留作历史记录。

## 1. 决策记录（2026-08-31，用户口述）

- **Flet 本地采用**：本机/macOS 个人使用正式采用 Flet，P1–P8 解冻开始执行。
- **公司部署独立门**：公司 Windows 部署仍受 `docs/decisions/COMPANY_ENVIRONMENT_CHECKLIST.md`（D1–D4）约束，不阻塞本地迭代。
- **公司环境新事实**：v1（纯标准库版）在公司内部环境运行没有任何问题；公司 Python 为 **3.13**（本机 `.venv` 为 3.12）。且据可行性报告修补 3 记录，公司内网已实测运行过 Flet 样片（Windows 字体反馈即来自该次运行）——`flet[all]==0.86.5` 在 Python 3.13 上的运行兼容性**事实上已验证**。仍待办的公司侧事项收窄为审批/分发类：
  - 内网镜像能否提供固定 Flet 版本及传递依赖（审批口径）；
  - 桌面宿主 Flet.app（约 134MB，不随 wheel 分发）的离线分发与 `FLET_VIEW_PATH` 方案（见 `workbench/DEPENDENCY_NOTES.md`，B1 改名前为 `prototypes/flet_workbench/DEPENDENCY_NOTES.md`）；
  - EXE 打包/签名策略与 localhost/WebSocket 政策（沿用 COMPANY_ENVIRONMENT_CHECKLIST）。
- **正式化策略：原地演进**。`prototypes/flet_workbench/` 升级为正式包 `workbench/`，保留全部已验证测试；不在 `app/` 下重建 UI（v1 保持原样，互不修改）。

## 2. 样片后增量（2026-08-31）

可行性报告归档（42 测试）之后、本文档之前完成的工作：

- **全页可编辑**：每日计划条目增/改/勾/删、工作记录编辑、项目元数据与行动标题改名、节点标题/备注编辑、节点资源（名称/链接可编辑，可添加、可删除）。
- **新领域模型**：`DayRecord`、`PlanItem`、`Resource`、`EDITABLE_PROJECT_FIELDS` 白名单；新活动种类 `plan_updated`、`worklog_updated`（均计入有意义活动）。
- **通用编辑组件** `components/editable.py`：悬停露铅笔、单击进入编辑、Enter/失焦提交、多行编辑器带保存/取消按钮。
- 测试 42 → 69（样片），主仓库 44 项无回归。
- 状态边界不变：所有写入经 `WorkspaceService` 显式方法；改行动名不刷新停滞计时；活动页只读。

## 3. 已知缺口（转入调整后 backlog）

| 缺口 | 去向 |
|---|---|
| Today「生成整理建议」按钮未接线 | P6′ `daily.organize_context` |
| 导航「想法」「归档」路由无页面，回落到项目总览 | P5′ |
| TextField 无 Esc 事件（Flet 0.86 平台限制） | 记录在案，不修 |
| 资源彩色标签只读不可编辑 | P5′ |
| 编辑不落盘（内存态，关闭即失） | P2′（本次最优先） |

## 4. 调整后 backlog（P1′–P8′）

### P2′ Markdown/JSON 真源（最优先，本次启动）

- 目录：`data-issue-vault/v2/`；Markdown 存叙事正文，JSON 存稳定 ID/状态/标签/revision。
- **新增**（原清单缺失）：每日计划（`days/<date>.json`）与工作记录（`days/<date>.md`）的存储布局。
- revision 冲突不静默覆盖：写前比对，不匹配抛 `StorageConflict`。
- Capture/想法原文不可覆盖；更新要求 expected revision。
- 测试：临时目录、中文路径、Windows 路径、路径逃逸；**测试与默认运行不触真实 vault**。

### P1′ 领域模型补齐

在样片已有模型（Project/OutlineNode/Action/Idea/Resource/DayRecord/PlanItem/ActivityEvent/Proposal）基础上补：

- `Capture`（与 Idea 区分的原始捕获）、`Outcome`（deliverable/decision/conclusion）、有类型 `Relation`；
- Idea 状态机 `pending / sorted / kept / archived`；
- Action 等待/延后排除条件（样片已实现，补全量接口测试）。

不再从零设计领域模型。

### P5′ UI 补缺

想法页、归档页、关系/标签编辑、晚间勾选流程。其余页面（项目总览/节点详情/Today/活动热力图/长期停滞）样片已达成并有契约测试。

### P3′ SQLite 可重建索引（降级为条件触发）

仅当启动全量扫描出现实测性能问题时实施；当前数据量 Markdown/JSON 全量读入足够。索引仍只存可重建数据，不作唯一真源。

### P4′ 旧数据显式导入

内容不变（预览→确认→复制，来源路径+哈希幂等，不动旧文件）。顺位后移。

### P6′ Fake AI Proposal

内容不变：`capture.organize`、`resource.suggest_metadata`、`project.review`、`daily.organize_context` 四动作全走 Proposal，接受/部分接受/拒绝均留 Activity。`project.review` 样片已有。

### P7′ OpenCode 边界

内容不变：只冻结 Protocol，MVP 不连真实服务；公司环境确认后再探测。

### P8′ 公司交接文档包

内容不变；补充第 1 节的公司新事实。

## 5. 执行顺序

1. 本文档 + 原清单指针 + 可行性报告附注（A）
2. 落盘最小闭环：包改名 `workbench/`、`storage/` 层、service 接线、`--vault` 参数、测试（B）
3. P1′ 领域补齐 → P5′ UI 补缺 → P6′ → P4′ / P8′
4. P3′ 条件触发；P7′ 等公司确认

## 6. 2026-08-31 晚间增量

- **P5′ 部分完成**：想法页（状态流转 pending/kept/archived，原文不可改写）、归档页（已归档想法可恢复 + 已完成/已取消行动只读）、项目首页（全部项目卡片，`/projects/{pid}` 单项目路由，AI 审查跟随当前项目）。
- **P7′ 接入面就绪**：`OpenAICompatibleRuntime`（纯标准库 SSE 流式，满足 RuntimeGateway 协议）+ `--provider fake|openai`、`--ai-base-url/--ai-model/--ai-api-key`（或 `WORKBENCH_AI_*` 环境变量）。默认仍 fake，行为不变。新增 `failed` 终态：传输失败/JSON 不可解析显式报错，不伪装 completed。端到端已用本地 OpenAI 兼容 stub 验证（提案渲染、接受流不变）。
- **真实端点待接入**：本机暂无可用端点（hermes 已删、opencode/ollama 未装、4096 未开）。任一 OpenAI 兼容端点（`opencode serve`、Ollama、LM Studio、aigate /v1）就绪后：

```bash
.venv/bin/python -m workbench.main --vault data-issue-vault/v2 \
  --provider openai --ai-base-url http://127.0.0.1:4096/v1 --ai-model <模型名>
```

- 编辑交互定稿：全站双击编辑，无常驻铅笔图标。测试 90 → 106。

React 备用分支（原清单第 13 节）随 Flet 本地采用而关闭；若公司侧最终否决 Flet，仅 UI 层回退，Python 领域/存储/测试保留。
