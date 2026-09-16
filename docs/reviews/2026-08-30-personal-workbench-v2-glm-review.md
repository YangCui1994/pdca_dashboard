# Personal Workbench v2 — GLM 独立审查清单

适用对象：与实施会话分离的 GLM 审查会话

审查模式：默认只读

被审对象：`prototypes/flet_workbench/`、Flet 可行性报告及其测试/截图证据

实施清单：`docs/plans/2026-08-30-personal-workbench-v2-glm-execution.md`

## 1. 审查职责

审查者只回答三个问题：

1. 样片是否真实满足实施清单的可验证行为？
2. 是否存在会导致数据丢失、架构锁死、虚假能力声明或公司环境误判的风险？
3. 现有证据足以建议 Flet、要求修补，还是必须交给用户决策？

输出只能是：

- `PASS`：证据完整，建议进入用户 Flet 选型确认。
- `BLOCK`：存在明确缺失或失败，实施者应做一次针对性修补。
- `ESCALATE`：技术事实已明确，但需要用户偏好或公司政策决定。

审查者不得：

- 未经用户许可直接修改实现。
- 重写整个样片。
- 开始正式 `app/` 迁移。
- 恢复用户已删除的路由文件。
- 读取真实 `data-issue-vault` 内容。
- 因为“可能更好”而要求引入 React、数据库、Node、Quill、自定义 Dart 或额外框架。
- 重复一轮没有新证据的全面审查。

## 2. 给独立 GLM 的审查提示

```text
你是 Personal Workbench v2 Flet 技术样片的独立审查者。只读检查以下内容：

1. AGENTS.md
2. docs/plans/2026-08-30-personal-workbench-v2-glm-execution.md
3. docs/reviews/2026-08-30-personal-workbench-v2-glm-review.md
4. docs/decisions/FLET_FEASIBILITY_REPORT.md
5. prototypes/flet_workbench/

不要修改代码。先核对 Git 和数据安全，再运行确定性测试和双模式验证，然后检查截图与 Artifact。所有结论必须引用文件、命令输出或截图路径。

最终只给 PASS、BLOCK 或 ESCALATE：
- PASS：证据完整，可以让用户决定正式采用 Flet；
- BLOCK：列出最多 5 个必须修复的问题，每个问题给出证据和最小修补范围；
- ESCALATE：说明需要用户选择的具体问题，不用技术术语掩盖偏好判断。

一次完整审查后只允许一次针对性复查，不开启新一轮开放式研究。
```

## 3. 审查输入完整性

- [ ] 实施清单存在且与当前样片阶段一致。
- [ ] `docs/decisions/FLET_FEASIBILITY_REPORT.md` 存在。
- [ ] 报告写明 Python、Flet、macOS 版本。
- [ ] 报告写明实际 GLM 模型/effort；不可见时为 `unknown`。
- [ ] 报告列出桌面/Web 实际启动命令。
- [ ] 报告列出测试命令与结果。
- [ ] 报告链接全部截图和 Artifact。
- [ ] 报告没有把 Windows/公司环境的未知项写成已验证。

任一核心输入不存在：`BLOCK`。

## 4. Gate 0 — Git 与真实数据安全

### 4.1 用户改动保护

- [ ] 运行 `git status --short --branch`。
- [ ] 确认以下用户改动没有被恢复或覆盖：

```text
D .agents/skills/model-routing/SKILL.md
M AGENTS.md
D docs/MODEL_ROUTING_PROFILE.md
D docs/MULTI_AGENT_PLAYBOOK.md
D docs/superpowers/plans/2026-08-29-pdca-model-routing-skill.md
D docs/superpowers/specs/2026-08-29-pdca-model-routing-skill-design.md
M tests/test_project_skill.py
```

- [ ] `git diff --name-only` 中除用户已有改动外，只出现本任务允许的新文档、样片和截图。
- [ ] 没有执行或留下 reset、checkout restore、clean 等破坏性处理痕迹。

### 4.2 Vault 边界

- [ ] 仅运行 `git status --short --ignored data-issue-vault`，不读取内容。
- [ ] 没有新的已跟踪真实数据。
- [ ] Fixture 中没有真实姓名、公司项目、内网地址、本机真实文件路径或 API 密钥。
- [ ] 样片运行不修改 `data-issue-vault` 时间戳和文件。

检查方式：

```bash
git diff --name-only
git status --short --ignored data-issue-vault
rg -n "api[_-]?key|token|password|secret|localhost:[0-9]+/v1" prototypes/flet_workbench docs/decisions
```

发现真实数据或 Vault 改写：`BLOCK`，并立即停止后续审查。

## 5. Gate 1 — 旧系统基线

- [ ] 运行：

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

- [ ] 如果 HTTP 测试只因端口权限失败，取得权限后运行：

```bash
python3 -m unittest tests.test_server -v
```

- [ ] 报告中的数量与实际一致。
- [ ] 新样片没有改变旧系统行为。

预期：共 44 项，获得回环权限后全部通过。

真实测试回归：`BLOCK`。单纯沙箱权限限制可记录为环境限制，不得写成代码失败。

## 6. Gate 2 — 依赖与模块边界

### 6.1 依赖

- [ ] 使用 Python 3.12。
- [ ] `requirements.txt` 固定 `flet[all]==0.86.5`。
- [ ] 没有 Node、React、FastAPI、pystray、更新器、Quill 或自定义 Dart 依赖。
- [ ] `DEPENDENCY_NOTES.md` 记录 Flet/Flutter 公司审批未知。
- [ ] 样片不依赖 Codex 私有 Python 路径。

### 6.2 分层

- [ ] `main.py` 只负责组合和启动。
- [ ] views、components、runtime、services、domain 分开。
- [ ] 运行：

```bash
rg -n "import flet|from flet" prototypes/flet_workbench/domain prototypes/flet_workbench/runtime prototypes/flet_workbench/services
```

预期：无输出。

- [ ] Domain/Runtime/Service 测试无需启动 Flet 窗口。
- [ ] Flet callback 没有复制停滞规则、Heatmap 聚合或 Proposal 权限逻辑。
- [ ] 没有单个文件承担绝大多数页面和业务规则。

核心层依赖 Flet 或样片退化为单文件：`BLOCK`。

## 7. Gate 3 — TDD 与行为证据

### 7.1 测试先行证据

- [ ] 检查 GLM 检查点报告或提交历史，确认每个 tracer bullet 有 RED 和 GREEN 命令。
- [ ] 测试通过公共接口，不检查私有字段或实现调用次数。
- [ ] 没有一次性先写全部测试再补全部实现。
- [ ] 每次修补后重新运行相关测试。

没有历史 RED 证据但最终测试有效：记录为流程偏差；若关键权限边界未被测试则 `BLOCK`。

### 7.2 样片测试

运行：

```bash
.venv/bin/python -m unittest discover -s prototypes/flet_workbench/tests -p 'test_*.py' -v
```

必须验证：

- [ ] Runtime 状态严格按 `queued → running → using_tool → completed`。
- [ ] 至少 100 个有序 using_tool 事件。
- [ ] completed 只出现一次。
- [ ] Proposal 接受前 Workspace snapshot 不变。
- [ ] Proposal 拒绝后状态不变。
- [ ] 15 天进行中 Action 被标记。
- [ ] waiting/deferred/completed/cancelled 不被标记。
- [ ] 查看页面不算有意义更新。
- [ ] Heatmap 不统计浏览事件。
- [ ] Artifact 不引用 CDN 或外部 HTTP 资源。

任一关键行为无测试或失败：`BLOCK`。

## 8. Gate 4 — UI 合同与视觉

### 8.1 页面结构

- [ ] 左侧导航包含 Today、Ideas、Projects、Activity、Archive。
- [ ] Projects 默认高亮。
- [ ] 项目总览包含：
  - 项目目标；
  - 当前阶段；
  - 当前焦点；
  - 下一里程碑；
  - 负责人；
  - 项目大纲；
  - 今日任务；
  - 14 天活动；
  - 长期停滞。
- [ ] 项目大纲节点可以点击。
- [ ] 节点详情持续显示大纲二级导航。
- [ ] 节点详情支持自由 Markdown、相关链接、标签和显式关系。
- [ ] Today 是简单计划勾选，不是 Kanban。
- [ ] “待整理想法”和“整理今日上下文”上下排列。
- [ ] Activity Heatmap 可点击日期。
- [ ] 右侧 AI 面板有运行中、待确认、接受和拒绝状态。

### 8.2 视觉对照

参考图：

```text
docs/product/assets/approved-ui/
```

样片截图：

```text
docs/decisions/assets/flet-spike/
```

- [ ] 使用相近宽屏尺寸比较同一状态。
- [ ] 浅色、克制紫色、编辑型工作台层级正确。
- [ ] P0/P1/P2 已修复。
- [ ] P3 只记录，没有无止境打磨。
- [ ] 没有用截图伪装可交互页面。
- [ ] 主导航、节点点击、日期点击、AI 运行和 Proposal 确认均实际可用。

主流程不可用或 P1 未修复：`BLOCK`。纯审美偏好且功能完整：`ESCALATE` 给用户。

## 9. Gate 5 — Fake Runtime 和 UI 响应

- [ ] 运行“项目审查”后 UI 显示真实事件序列，不是一次性填充结果。
- [ ] 100 个事件期间仍能切换节点或滚动页面。
- [ ] UI 更新使用异步任务，不阻塞主线程。
- [ ] 面板区分事实、AI 推断、外部知识和 Proposal。
- [ ] 接受前正式状态不变。
- [ ] 接受后只有 Proposal 指定字段变化。
- [ ] 拒绝不改变正式状态。
- [ ] 运行失败有可见错误，不伪装 completed。

只做视觉动画、没有 Runtime 公共接口：`BLOCK`。

## 10. Gate 6 — Artifact

### 10.1 文件

- [ ] `artifacts/project-flow.html` 存在。
- [ ] 文件断网可打开。
- [ ] 不引用 CDN、远程字体、远程 JS 或远程 CSS。
- [ ] 展示项目、Decision、Resource、Action 的关系。
- [ ] 节点可点击并切换详情。
- [ ] 包含来源项目 ID。

### 10.2 内嵌

- [ ] 报告明确写 `supported / unsupported / blocked`。
- [ ] 若 supported，使用 Flet 当前版本公开能力，不是自定义 Dart。
- [ ] 若 unsupported，UI 没有伪造内嵌成功。
- [ ] 内嵌失败的错误或官方限制有证据。

### 10.3 外部打开

- [ ] 工作台可以打开本地 Artifact。
- [ ] 无互联网时仍能交互。
- [ ] 工作台中保留 Artifact 来源和文件路径。
- [ ] 不把任意不可信路径拼成可执行命令。

外部打开失败：`BLOCK`。仅内嵌不支持但外部打开通过：`ESCALATE`，由用户决定是否接受。

## 11. Gate 7 — 桌面与动态 Web

- [ ] 报告记录实际 `flet --help` 所支持的命令。
- [ ] macOS 桌面模式启动通过。
- [ ] 本地动态 Web 启动通过。
- [ ] Web 只绑定 localhost，不暴露到局域网。
- [ ] 两种模式使用相同 Fixture、WorkspaceService 和 FakeRuntime。
- [ ] 断开互联网后固定功能可用。
- [ ] 报告没有声称 Windows EXE 已通过。
- [ ] 报告没有声称公司批准 Flet/Flutter。

其中一种本机模式因代码失败：`BLOCK`。因宿主环境无法提供窗口/浏览器但代码和测试完整：记录限制并 `ESCALATE`。

## 12. Gate 8 — Flet/React 决策评分

逐项填写，不使用模糊的“基本可以”：

| 指标 | PASS 条件 | 结果 | 证据 |
|---|---|---|---|
| UI 还原 | 无 P0/P1/P2，用户主流程可操作 |  |  |
| 项目大纲 | 总览与节点页导航完整 |  |  |
| Fake 流式面板 | 100 事件不阻塞，状态真实 |  |  |
| Proposal 边界 | 确认前零正式写入 |  |  |
| Heatmap | 有意义事件聚合准确 |  |  |
| Artifact 外部打开 | 离线可用且来源可追溯 |  |  |
| Artifact 内嵌 | supported / unsupported / blocked |  |  |
| 桌面模式 | macOS 本机通过 |  |  |
| 动态 Web | localhost 本机通过 |  |  |
| 分层 | 核心层零 Flet import |  |  |
| 公司 Windows | 明确标为待验证 |  |  |

判定规则：

- 任一数据安全、Proposal 边界、分层或外部 Artifact 项失败：`BLOCK`。
- 只有内嵌 Artifact 不支持：`ESCALATE`。
- 全部可验证项通过且未知项如实标注：`PASS`。
- 不因为 React 生态更大而自动否决 Flet。
- 不因为用户熟悉 Python 而忽略 Artifact 或公司构建风险。

## 13. 正式架构前置审查

只有用户确认 Flet 后才使用本节。

### 13.1 Markdown/JSON 真源

- [ ] 所有正式叙事内容存在于 Markdown。
- [ ] 所有结构元数据存在于 JSON。
- [ ] SQLite 删除后可以重建。
- [ ] 删除索引不丢失 Project、Resource、Relation、Activity。
- [ ] 外部 Markdown 修改的冲突策略有测试。
- [ ] revision 冲突不静默覆盖。

### 13.2 旧数据导入

- [ ] 导入前只有预览。
- [ ] 未确认时零写入。
- [ ] 导入只复制，不移动原文件。
- [ ] 来源路径和哈希记录完整。
- [ ] 重复导入幂等。
- [ ] 失败可安全重试。

### 13.3 正式 Proposal

- [ ] Fake/OpenCode/Direct API 都只能输出 Proposal。
- [ ] Runtime 不直接访问存储写接口。
- [ ] 部分接受只应用所选字段。
- [ ] 接受、拒绝、失败均有 Activity。
- [ ] UI 不按 Runtime 类型复制业务规则。

## 14. 公司/Windows 审查

在公司环境执行，不得在 macOS 报告中提前勾选：

- [ ] Windows 版本和 Python 3.12 可用。
- [ ] 公司镜像可提供固定 Flet 及传递依赖。
- [ ] Visual Studio Desktop C++ / Flutter 构建工具是否批准。
- [ ] 外部 EXE 禁令是否允许内部编译和签名后的 EXE。
- [ ] 若不允许 EXE，Flet 动态 Web 资产是否批准。
- [ ] localhost 端口和 WebSocket 是否允许。
- [ ] 中文路径、长路径、LocalAppData 和文件权限通过。
- [ ] OpenCode `serve`、SSE、session、permission、MCP 和 agent 能力经过实际探测。
- [ ] 内部模型 API、证书、代理和密钥位置不写入仓库。

未验证项一律写 `unknown`，不能推断。

## 15. 审查输出模板

```text
# Flet Spike Independent Review

Verdict: PASS / BLOCK / ESCALATE

Reviewer route:
- requested model/effort:
- surfaced effective model/effort: <value or unknown>

Evidence:
- Git/data safety:
- Legacy tests:
- Spike tests:
- Desktop mode:
- Dynamic Web:
- UI screenshots:
- Runtime 100-event behavior:
- Proposal boundary:
- Artifact embedded:
- Artifact external/offline:

Blocking findings (最多 5 项):
1. [requirement] [file/command/screenshot evidence] [minimum repair]

User decisions required:
1. ...

Repeated review:
- full review count: 1
- targeted recheck count: 0 or 1
- new evidence produced: yes/no

Recommended next action:
- request user Flet decision
- one bounded repair pass
- investigate one named company policy item
```

## 16. 针对性复查

只有第一次结论为 `BLOCK` 且实施者完成最小修补后执行：

- [ ] 只复查原 BLOCK 项和受影响回归测试。
- [ ] 不重新提出新的开放式架构偏好。
- [ ] 不重新做全套网页研究。
- [ ] 如果同一项仍失败，保持 BLOCK 并停止。
- [ ] 如果出现需要用户偏好的事实，改为 ESCALATE。
- [ ] 复查后关闭审查会话，不启动第三轮。
