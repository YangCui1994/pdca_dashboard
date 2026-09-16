# Personal Workbench v2 — GLM 执行清单

状态：待执行

执行模型：当前电脑上的 GLM（具体模型标识和 effort 若界面不展示，记录为 `unknown`）

第一阶段目标：完成隔离的 Flet 技术样片和可审查证据，停在 Flet/React 决策门

配套审查：`docs/reviews/2026-08-30-personal-workbench-v2-glm-review.md`

## 1. 执行边界

这不是一次直接重写正式应用的任务。GLM 必须先完成 Flet 技术样片，在用户确认技术路线之前：

- 不修改 `app/` 下的现有 Python 原型。
- 不修改现有 `tests/`，除非只是修复由本任务新文件引起的测试发现问题，并先向用户报告。
- 不读取、复制、重命名或删除 `data-issue-vault/` 中的真实内容。
- 不恢复当前工作树中已删除的模型路由文件。
- 不安装 Node.js，不创建 React/Vite 项目。
- 不实现 OpenCode、Direct API、MCP、Skill 或多 Agent Runtime。
- 不引入 pystray、自动更新器、Inno Setup、自定义 Dart/Flutter 控件或 Quill 编辑器。
- 不执行破坏性 Git 命令，不清理用户工作树，不提交用户已有改动。

当前已知工作树中存在用户拥有的改动：

```text
D .agents/skills/model-routing/SKILL.md
M AGENTS.md
D docs/MODEL_ROUTING_PROFILE.md
D docs/MULTI_AGENT_PLAYBOOK.md
D docs/superpowers/plans/2026-08-29-pdca-model-routing-skill.md
D docs/superpowers/specs/2026-08-29-pdca-model-routing-skill-design.md
M tests/test_project_skill.py
```

这些改动必须保留原状，不能恢复、覆盖或混入本任务提交。

## 2. 给 GLM 的启动提示

将下面整段作为 GLM 的第一条任务消息。若 GLM 运行在 OpenCode 或其他 Harness 中，先把工作目录设为本仓库根目录。

```text
你正在实现 Personal Workbench v2 的 Flet 技术样片。严格读取并按顺序执行：

1. AGENTS.md
2. docs/plans/2026-08-30-personal-workbench-v2-glm-execution.md
3. docs/reviews/2026-08-30-personal-workbench-v2-glm-review.md
4. README.md
5. docs/PROJECT_STRUCTURE.md

你的写入范围仅限计划当前步骤明确允许的文件。先测试后实现，一次只做一个 RED→GREEN 纵向行为。不要修改现有 app/、现有 tests/、真实 data-issue-vault/ 或用户已有 Git 改动。

第一阶段只完成 prototypes/flet_workbench/ 技术样片、脱敏 fixture、测试、截图和 FLET_FEASIBILITY_REPORT。完成后必须停止，不得自行开始正式架构迁移。

每完成一个检查点，报告：
- 完成的 checklist 编号；
- 实际修改文件；
- 先失败后通过的测试命令与结果；
- 未解决风险；
- 是否达到下一个检查点。

若模型/effort、Flet 桌面模式、Flet Web、内嵌 Artifact 或系统浏览器能力不可用，必须如实记录实际情况，不得假装执行成功。
```

## 3. 执行方式与 Agent 使用

默认使用一个 GLM 实施会话。多 Agent 不是常规要求。

- 实施者：唯一写入者，顺序执行本清单。
- 可选只读核验者：只在 Flet API、双模式或 Artifact 能力存在不确定时使用，最多一个，depth = 1。
- 独立审查者：样片完成后开启另一个 GLM 会话，严格使用审查清单；审查者默认不得修改代码。
- 根协调者：用户或当前主会话，决定 `PASS / BLOCK / ESCALATE` 后的技术路线。

若 Harness 支持选择模型：

- 实施可请求 GLM 的较高推理档。
- 独立审查使用与实施分离的会话。
- 若实际模型不可见，记录 `unknown`，不推断。

禁止两个 Agent 同时编辑同一目录。所有自动测试、哈希、文件枚举和截图尺寸检查使用本地工具完成，不交给额外 Agent 猜测。

## 4. 阶段 A — 安全基线

### A1. 工作树确认

- [ ] 运行 `git status --short --branch`。
- [ ] 确认上文列出的用户改动仍存在。
- [ ] 确认尚未出现 `prototypes/flet_workbench/` 的残留半成品；如存在，先报告，不覆盖。
- [ ] 确认 `python3.12 --version` 为 Python 3.12.x。
- [ ] 确认不需要 Node.js。

预期：当前电脑可调用 Python 3.12.13；`glm` 和 `opencode` 不一定在 shell PATH，这不阻止用户通过当前图形/Harness 会话运行 GLM。

### A2. 旧系统测试基线

- [ ] 运行：

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

- [ ] 若仅 HTTP 测试因为沙箱不能绑定回环端口而失败，申请对应权限后仅重跑：

```bash
python3 -m unittest tests.test_server -v
```

- [ ] 将测试数量、通过数量、失败原因记录到 `docs/decisions/FLET_FEASIBILITY_REPORT.md` 的 Baseline 部分。

预期：共 44 项测试；获得本机回环权限后全部通过。若出现真实回归，停止并报告，不进入样片实现。

### A3. 数据安全基线

- [ ] 仅运行 `git status --short --ignored data-issue-vault`，不要打开被忽略文件。
- [ ] 记录被忽略项目数量，不记录文件内容。
- [ ] 保存开始时的 `git status --short` 输出，供审查阶段对比。

停止条件：任何命令将改写真实 Vault、删除文件或需要读取真实内容时立即停止。

## 5. 阶段 B — Python/Flet 环境

### B1. 建立隔离环境

- [ ] 创建仓库内 `.venv`：

```bash
python3.12 -m venv .venv
```

- [ ] 使用虚拟环境 Python 升级 pip。
- [ ] 安装固定版本：

```bash
.venv/bin/python -m pip install 'flet[all]==0.86.5'
```

- [ ] 创建 `prototypes/flet_workbench/requirements.txt`，只写：

```text
flet[all]==0.86.5
```

- [ ] 生成 `prototypes/flet_workbench/DEPENDENCY_NOTES.md`，记录：
  - Python/Flet 版本；
  - 安装来源；
  - Flet/Flutter 运行资产；
  - 该依赖尚未获得公司内网批准；
  - 未安装 Node、pystray、Quill、更新器或自定义扩展。

- [ ] 验证：

```bash
.venv/bin/python -c "from importlib.metadata import version; print(version('flet'))"
.venv/bin/flet --help
```

若安装需要外网或系统权限，由 GLM 先请求用户批准。安装失败时记录完整错误，禁止静默改用其他 Flet 版本。

### B2. 建立可导入目录

使用下列结构。计划原先的连字符目录已改为下划线，因为 Python 包名不能安全使用连字符。

```text
prototypes/
  __init__.py
  flet_workbench/
    __init__.py
    main.py
    domain/
      __init__.py
      models.py
      fixtures.py
    runtime/
      __init__.py
      contracts.py
      fake_runtime.py
    services/
      __init__.py
      workspace_service.py
    components/
      __init__.py
      navigation.py
      project_outline.py
      heatmap.py
      ai_panel.py
      artifact_panel.py
    views/
      __init__.py
      project_overview.py
      node_detail.py
      today.py
      activity.py
    artifacts/
      project-flow.html
    tests/
      __init__.py
      test_fake_runtime.py
      test_workspace_service.py
      test_ui_contract.py
      test_artifact.py
    requirements.txt
    DEPENDENCY_NOTES.md
```

约束：

- `main.py` 只负责组合页面和启动，不承载领域规则。
- `domain/`、`runtime/`、`services/` 不得 `import flet`。
- Fixture 只能使用虚构项目、人员、文件路径和内网链接。
- 样片不写入 `data-issue-vault`。

## 6. 阶段 C — TDD Tracer Bullets

严格一次完成一个 RED→GREEN；不要先把所有测试一次写完。

### C1. Runtime 状态序列

行为：调用 Fake Runtime 后可观察到 `queued → running → using_tool → completed`。

- [ ] RED：只新增 `test_fake_runtime.py` 中的一个测试。
- [ ] 运行并确认因模块/行为不存在而失败。
- [ ] GREEN：实现最小 `RuntimeGateway` Protocol、`RunEvent` 和 `FakeRuntime.events()`。
- [ ] 再次运行并通过。

命令：

```bash
.venv/bin/python -m unittest prototypes.flet_workbench.tests.test_fake_runtime -v
```

### C2. 100 个流式事件

行为：Fake Runtime 生成至少 100 个有序 `using_tool` 事件，序号不重复，最终只完成一次。

- [ ] RED：新增一个公共接口行为测试。
- [ ] GREEN：最小实现，不使用真实等待让测试变慢。
- [ ] 测试中不得依赖 Flet 控件。

### C3. Proposal 确认边界

行为：Runtime 完成后只返回 Proposal；在 `accept_proposal()` 前，Workspace snapshot 完全不变。

- [ ] RED：通过 `WorkspaceService` 公共接口比较操作前后 snapshot。
- [ ] GREEN：实现内存 WorkspaceService 和显式接受动作。
- [ ] 增加拒绝 Proposal 后状态不变的第二个纵向循环。

### C4. 长期停滞规则

行为：进行中且 15 天没有有意义更新的 Action 被标记；等待、延后、完成和取消不标记。

- [ ] 先实现一个“15 天进行中”失败测试并通过。
- [ ] 再逐个增加排除状态测试。
- [ ] 查看页面本身不得刷新 `last_meaningful_update_at`。

### C5. Heatmap 聚合

行为：只统计任务完成、内容更新、资源加入、Decision 确认和 Proposal 接受等有意义事件；浏览页面不计数。

- [ ] RED：通过 WorkspaceService 查询日期聚合。
- [ ] GREEN：实现最小聚合。
- [ ] 覆盖跨项目筛选。

检查点 C：

```bash
.venv/bin/python -m unittest discover -s prototypes/flet_workbench/tests -p 'test_*.py' -v
```

预期：全部通过；Runtime/Service 测试不需要打开窗口。

## 7. 阶段 D — Flet 样片 UI

批准的视觉参考位于当前电脑：

```text
/Users/yang/.codex/generated_images/01a04bad-64c1-7473-bcd7-af51b838f3b1/exec-b12c77cb-6281-44b2-97e3-a823963f8e63.png
/Users/yang/.codex/generated_images/01a04bad-64c1-7473-bcd7-af51b838f3b1/exec-891dd236-c3c7-404d-8e0e-6345ba00c9c4.png
```

- [ ] 视觉实现前先查看这两张图。
- [ ] 只将确认不含真实公司信息的参考图复制到 `docs/product/assets/approved-ui/`。
- [ ] 采用浅色、克制紫色、编辑型工作台风格。
- [ ] 不使用自定义图片代替标准图标；优先使用 Flet 自带 Material 图标。

### D1. UI 合同测试

先添加 `test_ui_contract.py`，通过公共 view builder 验证：

- [ ] 左侧存在 Today、Ideas、Projects、Activity、Archive。
- [ ] 项目总览存在项目摘要、大纲、当前关注、今日任务和长期停滞区域。
- [ ] 右侧存在 AI 面板及运行状态。
- [ ] 节点页持续包含项目大纲。
- [ ] Today 使用简单计划勾选，不实现 Kanban。

测试只检查用户可见标签、route 和 callback 是否存在，不检查私有控件树细节。

### D2. 项目总览

- [ ] 左栏固定宽度，当前 `Projects` 高亮。
- [ ] 中间顶部显示目标、阶段、当前焦点、下一里程碑和负责人。
- [ ] 项目大纲节点：
  - 目标与边界；
  - 参与者与职责；
  - 当前进展；
  - 关键判断；
  - 测试资源；
  - 资料与链接；
  - 待推进事项。
- [ ] 点击节点进入节点详情。
- [ ] 右侧展示当前要关注、今日任务、长期停滞和 14 天活动。

### D3. 节点详情

- [ ] 左侧保留主导航。
- [ ] 中间左边保留项目大纲二级导航。
- [ ] 内容区展示自由 Markdown、相关文件链接、标签和显式关系。
- [ ] 相关文件只是虚构元数据卡，不读取本机文件。
- [ ] 可返回项目总览。

### D4. Today 与 Activity

- [ ] Today 展示简单计划勾选、工作记录、待整理想法、整理上下文建议和快速记录。
- [ ] “待整理想法”和“整理今日上下文”上下排列，不并排。
- [ ] Activity 展示 GitHub 风格 Heatmap。
- [ ] 点击日期后显示当日有意义事件。
- [ ] 长期停滞区域明确显示超过 14 天未更新的 Action。

### D5. Fake AI 面板

- [ ] 提供“运行项目审查”按钮。
- [ ] 使用 `page.run_task` 或等价异步方式消费 Fake Runtime。
- [ ] 流式更新时界面仍可切换项目节点。
- [ ] 面板区分事实、AI 推断、外部知识和待确认 Proposal。
- [ ] 用户接受 Proposal 后才调用 WorkspaceService。
- [ ] 拒绝后正式状态不变。

禁止在 UI callback 中复制领域规则。

## 8. 阶段 E — Artifact 验证

### E1. 本地 Artifact

- [ ] 创建完全脱敏的 `artifacts/project-flow.html`。
- [ ] 文件必须自包含基础 CSS/JavaScript，断网仍可点击节点和切换详情。
- [ ] 页面展示“项目 → 决策 → 资源 → 下一行动”的交互关系。
- [ ] 同时保留一段 Mermaid 源文本，明确标注“仅用于 Mermaid 能力探测”。
- [ ] 不通过 CDN 加载 Mermaid。

### E2. 内嵌能力

- [ ] 先检查当前 Flet 版本是否提供无需自定义 Dart 的官方 WebView/HTML 嵌入能力。
- [ ] 若可用，在 Artifact Panel 内嵌本地 HTML，并记录 API、平台和限制。
- [ ] 若不可用，展示 Artifact 摘要、文件路径和“在浏览器打开”按钮。
- [ ] 不新增自定义 Flutter/Dart 扩展。

### E3. 外部浏览器

- [ ] 使用受控的本地 `file://` URI 或 localhost 静态服务打开 Artifact。
- [ ] 验证无互联网时仍能交互。
- [ ] 验证从 Artifact 返回工作台时来源项目可追溯。

### E4. Artifact 测试

- [ ] `test_artifact.py` 验证文件存在、不引用 CDN/HTTP 外部资源、包含项目来源 ID 和交互脚本。
- [ ] 内嵌不可用不是自动伪造成功；应记录为 `unsupported`。

## 9. 阶段 F — 桌面/Web 双模式

先运行 `.venv/bin/flet --help`，以当前安装版本展示的真实参数为准。

- [ ] 桌面模式启动样片。
- [ ] 动态 Web 模式绑定 `127.0.0.1`，不要暴露到局域网。
- [ ] 两种模式使用相同 Fixture、WorkspaceService 和 FakeRuntime。
- [ ] 断开互联网后验证项目、Today、Heatmap、Proposal 和 Artifact 外部打开。
- [ ] 记录启动命令、端口、Flet 版本和平台。
- [ ] 不在本阶段构建 macOS app bundle 或 Windows EXE。

## 10. 阶段 G — 可视化与性能证据

- [ ] 为以下状态各保存一张截图：
  - 项目总览；
  - 节点详情；
  - Today；
  - Activity Heatmap；
  - AI 流式运行中；
  - Proposal 待确认；
  - Artifact 内嵌或外部打开说明。
- [ ] 使用与参考图接近的桌面宽屏尺寸。
- [ ] 保存到 `docs/decisions/assets/flet-spike/`。
- [ ] 对照批准参考图记录 P0/P1/P2/P3：
  - P0：核心页面不可用；
  - P1：主流程或布局严重偏差；
  - P2：显著视觉/交互偏差；
  - P3：可后续修饰。
- [ ] 修复 P0/P1/P2，P3 只记录，不循环打磨。
- [ ] 手工观察 100 事件运行期间是否冻结，并记录开始/结束时间；不要估计不可见性能指标。

## 11. 阶段 H — Flet 可行性报告

创建 `docs/decisions/FLET_FEASIBILITY_REPORT.md`，内容必须包括：

1. 环境和实际 Flet/Python 版本。
2. 旧系统测试基线。
3. 样片文件和运行命令。
4. 桌面/Web 验证结果。
5. UI 对照截图与问题列表。
6. Fake Runtime 100 事件证据。
7. Proposal 写入边界测试。
8. Artifact：
   - 内嵌：supported / unsupported / blocked；
   - 外部打开：PASS / BLOCK；
   - 离线：PASS / BLOCK。
9. 核心层是否存在 Flet import。
10. macOS 结果和 Windows/公司环境未知项。
11. 推荐结果：
    - `PASS`：建议采用 Flet；
    - `BLOCK`：实现或测试尚未完成；
    - `ESCALATE`：需要用户决定是否接受外部浏览器 Artifact，或公司政策未知。

样片完成后必须停止，向用户提交报告和截图，不得自行开始正式 `app/` 重构。

## 12. Flet 获批后的正式实施 Backlog

> **2026-08-31 起以调整版为准**：`docs/plans/2026-08-31-workbench-v2-formalization-adjustment.md`（Flet 已获本地采用；P2′ 落盘提为最优先，P1′/P5′ 依样片进度重排）。本节保留作历史记录。

以下任务仅在用户明确确认 Flet 后执行。

### P1. 领域模型

- [ ] 定义 Project、OutlineNode、Capture、Idea、Action、Outcome、Resource、Relation、Proposal、ActivityEvent。
- [ ] 全量项目与轻量项目使用同一 Project 聚合根。
- [ ] Outcome 区分 `deliverable / decision / conclusion`。
- [ ] Idea 状态为 `pending / sorted / kept / archived`。
- [ ] Action 明确定义等待和延后排除条件。
- [ ] 每个行为先写公共接口测试。

### P2. Markdown/JSON 真源

- [ ] 在 `data-issue-vault/v2/` 建立版本化目录。
- [ ] Markdown 保存原始输入和叙事正文。
- [ ] JSON 保存稳定 ID、状态、标签、关系、revision 和时间戳。
- [ ] Capture 原文不可覆盖。
- [ ] 更新要求 expected revision，冲突不静默覆盖。
- [ ] 测试中文路径、Windows 路径和路径逃逸。

### P3. SQLite 可重建索引

- [ ] 索引放在 `data-issue-vault/v2/.index/workbench.sqlite`。
- [ ] 索引只存可从 Markdown/JSON 重建的数据。
- [ ] 删除索引后可完整重建。
- [ ] UI 不得把 SQLite 当唯一真源。
- [ ] 审查者独立检查重建一致性。

### P4. 旧数据显式导入

- [ ] 只扫描旧目录元数据和用户明确选择的内容。
- [ ] 先生成导入预览。
- [ ] 用户确认后复制到 v2。
- [ ] 用来源路径和内容哈希保证幂等。
- [ ] 不删除、不移动、不原地改写旧文件。

### P5. 正式 UI

- [ ] Projects、项目总览和节点页。
- [ ] Resource、Tag、Outcome 和有类型 Relation。
- [ ] Ideas 和轻量项目升级。
- [ ] Today 简单计划和晚间勾选。
- [ ] Activity Heatmap。
- [ ] Archive 恢复。
- [ ] 14 天长期停滞。

### P6. Fake AI Proposal

- [ ] 实现 `capture.organize`。
- [ ] 实现 `resource.suggest_metadata`。
- [ ] 实现 `project.review`。
- [ ] 实现 `daily.organize_context`。
- [ ] 每次运行冻结 runtime 和 action。
- [ ] 所有输出先进入 Proposal。
- [ ] 接受/部分接受/拒绝均留 Activity 记录。

### P7. OpenCode 边界

- [ ] 只冻结 OpenCodeAdapter 和 DirectAPIAdapter Protocol。
- [ ] MVP 不连接真实服务。
- [ ] UI 不按 runtime 类型写业务分支。
- [ ] 公司环境确认后再探测 `serve`、OpenAPI、SSE、session、permission、MCP 和 agent。

### P8. 公司交接

- [ ] 完成 PRODUCT_SPEC、UX_SPEC、ARCHITECTURE、DATA_CONTRACTS。
- [ ] 完成 AI_RUNTIME_CONTRACT 和 TEST_AND_ACCEPTANCE。
- [ ] 完成 COMPANY_ENVIRONMENT_CHECKLIST。
- [ ] 完成 GLM_START_HERE、GLM_TASK_TEMPLATE 和 IMPLEMENTATION_STATUS。
- [ ] 交付脱敏 Fixture、截图、固定依赖清单、测试证据和已知问题。

## 13. React 备用分支

只有 Flet 报告被用户判定为不合格后才执行：

- [ ] 保留已经验证的 Python domain/storage/runtime/tests。
- [ ] 增加 FastAPI/Pydantic API。
- [ ] 此时才安装 Node 22。
- [ ] 使用 React/TypeScript/Vite 实现 UI 和沙箱化 HTML Artifact。
- [ ] 不改成全 TypeScript。
- [ ] 不重写已通过的 Python 领域行为。

## 14. 每个 GLM 检查点的汇报模板

```text
检查点：
状态：PASS / BLOCK / ESCALATE
实际模型/effort：<可见值或 unknown>
改动文件：
- ...

RED 证据：
- 命令：
- 预期失败：
- 实际失败：

GREEN 证据：
- 命令：
- 结果：

未解决风险：
- ...

用户已有改动是否保持原样：是/否
真实 Vault 是否未读取、未改动：是/否
下一步：<仅填写清单中的下一项；到阶段 H 时填写“等待用户决策”>
```

## 15. 提交边界

除非用户明确要求提交，否则 GLM 只完成文件和验证，不自行提交。

允许的最小提交点：

1. `docs: add glm execution and review checklists`
2. `test: define flet spike runtime contracts`
3. `experiment: add isolated flet workbench spike`
4. `docs: record flet feasibility evidence`

每次只暂存本任务新文件。禁止使用 `git add -A`，禁止把上文用户已有改动纳入提交。
