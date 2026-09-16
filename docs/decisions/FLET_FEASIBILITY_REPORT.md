# Flet 可行性报告 — Personal Workbench v2 技术样片

日期:2026-08-30 · 报告状态:样片完成,等待用户 Flet/React 决策

实施模型:GLM(经 Claude Code Harness 运行,模型标识 `glm-5.3[1m]`);effort 档位界面不展示,记为 `unknown`。

实施清单:`docs/plans/2026-08-30-personal-workbench-v2-glm-execution.md`
审查清单:`docs/reviews/2026-08-30-personal-workbench-v2-glm-review.md`

## 1. 环境与版本

| 项 | 值 | 证据 |
|---|---|---|
| macOS | Darwin 24.6.0(APPLE M 系列本机) | `uname` |
| Python | 3.12.13(仓库内 `.venv`) | `python3.12 --version` |
| Flet | 0.86.5(flet / flet-cli / flet-desktop / flet-web 同版本) | `importlib.metadata.version('flet')` |
| pip | 26.2.1 | 安装日志 |
| Node | 未安装(不需要) | `which node` → 空 |

依赖明细与公司审批状态见 `prototypes/flet_workbench/DEPENDENCY_NOTES.md`(公司内网批准:未知)。

## 2. 旧系统测试基线

命令:`python3 -m unittest discover -s tests -p 'test_*.py' -v`

结果:**44 项全部通过(OK,1.6s)**,无沙箱端口问题,无需单独重跑 `tests.test_server`。开始时的 `git status --short` 已存档于 `docs/decisions/assets/flet-spike/baseline-git-status.txt`;样片收尾时旧系统 44 项仍全部通过(无回归)。

数据安全:`git status --short --ignored data-issue-vault` 计 3 个被忽略条目,内容未读取、未改动。用户既有改动(7 项 D/M)全程保持原状,未恢复、未提交。

## 3. 样片文件与运行命令

样片位于 `prototypes/flet_workbench/`(domain / runtime / services / components / views / tests / artifacts)。Fixture 全部为虚构数据(人名"林演示/陈示例"、域名 `*.internal.example.net`、虚构文件路径),不含真实姓名、公司项目、本机真实路径或密钥。

```bash
# 桌面模式
.venv/bin/flet run -m prototypes.flet_workbench.main

# 动态 Web 模式(仅本机回环)
.venv/bin/flet run --web -m prototypes.flet_workbench.main -p 8791 --host 127.0.0.1

# 样片测试(30 项)
.venv/bin/python -m unittest discover -s prototypes/flet_workbench/tests -p 'test_*.py' -v
```

TDD tracer bullet 汇总(C1–C5,RED→GREEN 全程留痕于会话执行记录):

| 行为 | 测试文件 | 结果 |
|---|---|---|
| Runtime 状态序列 queued→running→using_tool→completed | test_fake_runtime.py | PASS |
| ≥100 有序 using_tool 事件、序号唯一、completed 仅一次(104 事件,0.000s) | test_fake_runtime.py | PASS |
| Proposal 接受前 snapshot 不变;接受后变化;拒绝后不变 | test_workspace_service.py | PASS |
| 15 天无有意义更新的进行中 Action 标记;waiting/deferred/completed/cancelled 排除;查看不刷新 | test_workspace_service.py | PASS |
| Heatmap 只聚合有意义事件(7 条,浏览 2 条不计);跨项目筛选;查询零写入 | test_workspace_service.py | PASS |
| UI 合同(导航 5 项/总览区域/AI 面板/节点页大纲/Today 勾选非看板) | test_ui_contract.py | PASS |
| Artifact 自包含、零外部加载、来源 ID、交互脚本、Mermaid 探测块 | test_artifact.py | PASS |

流程偏差(如实记录):C3 的"拒绝"测试首跑即绿(reject 与 accept 在同一 GREEN 实现);C4 排除状态测试为一次批量补充(逐项立即通过);C5 三个测试一次 RED 后单次 GREEN。关键权限边界(Proposal 接受前零写入)有严格 RED 证据。

## 4. 桌面 / 动态 Web 验证

| 模式 | 命令 | 结果 |
|---|---|---|
| macOS 桌面 | `.venv/bin/flet run -m prototypes.flet_workbench.main` | PASS:Flet.app 客户端进程启动,8 个场景均正常渲染并截图 |
| 动态 Web | `flet run --web -m ... -p 8791 --host 127.0.0.1` | PASS:`lsof` 显示仅监听 `127.0.0.1:8791`(未暴露局域网),`curl` 返回 HTTP 200 |

两种模式使用同一份 Fixture、WorkspaceService、FakeRuntime(同一代码路径,仅启动方式不同)。

已弃用 API 警告:`ft.app()` 自 0.80.0 起提示改用 `ft.run()`(P3,正式实施时替换,不影响功能)。

## 5. UI 对照截图与问题列表

参考图:`docs/product/assets/approved-ui/`(2 张,经图像分析确认全部为虚构占位内容后复制)
样片截图:`docs/decisions/assets/flet-spike/`(窗口 1440×900, retina 2880×1800 裁剪):

1. `01-project-overview.png` — 摘要条/大纲/关注/今日任务/长期停滞/14 天热力图
2. `02-node-detail.png` — 节点页(用户发现的"子页面过窄"问题已修复:根 Row 补 `expand=True`)
3. `03-today.png` — 简单计划勾选;待整理想法与整理今日上下文**上下排列**
4. `04-activity-heatmap.png` — 8 周 GitHub 风格热力图 + 当日事件 + 长期停滞
5. `05-ai-streaming-node-switch.png` — 流式运行中(36/106 事件)**同时已切换到节点页** → 界面不阻塞的直接证据
6. `06-proposal-awaiting.png` — 待确认 Proposal:事实(绿)/AI 推荐(紫)/外部知识(蓝)、更新范围、确认/暂不按钮
7. `07-artifact-external.png` — 经应用内按钮以 `file://` 在浏览器打开,来源项目 ID 同框可见
8. `08-web-mode.png` — Web 模式浏览器渲染

问题列表(对照参考图):

- **P0/P1/P2:无**(发现一处 P1 级"节点页内容区未撑满",已当场修复并有截图 02 复核)
- **P3(仅记录,不打磨)**:
  1. 系统标题栏为默认 "flet",未自定义应用名;
  2. AI 面板空闲态留白较大,参考图支持收起,样片未实现收起交互;
  3. 热力图因 fixture 仅约 2 周事件而多空点(演示数据量,非渲染缺陷);
  4. `ft.app()` 弃用警告;
  5. 参考图节点页的"未解决的缺口"警示块与资料表格 Tab,样片以简化卡片代替。

手工观察记录:100+ 事件流式运行期间(约 1.6s,每 6 事件刷新一次)导航可即时响应、无冻结(证据 05);未测量不可见性能指标。

## 6. Fake Runtime 100 事件证据

- 单测断言 ≥100(实际 104 个 using_tool 事件)、seq 严格递增无重复、completed 恰一次,整组测试 0.000s(无 sleep);
- UI 侧:AI 面板逐事件显示工具名与计数(截图 05 中段 36 事件、截图 06 完成态 106 事件);
- 消费方式:`page.run_task` 后台异步任务逐事件更新,不阻塞 UI 线程。

## 7. Proposal 写入边界

- 接受前:`service.snapshot()` 与运行前完全一致(单测断言);
- 拒绝后:snapshot 不变(单测断言;UI 拒绝走同一 `WorkspaceService.reject_proposal`);
- 接受后:仅 Proposal 声明字段变化(action.status→in_progress),并追加一条 `proposal_accepted` Activity;
- UI 接受/拒绝按钮仅转发用户决定给 WorkspaceService,回调内无领域规则。

## 8. Artifact

| 项 | 结论 | 证据 |
|---|---|---|
| 本地文件 | 存在、自包含(内联 CSS/JS) | `artifacts/project-flow.html`;test_artifact 5 项 PASS |
| 外部引用 | 零(src/href/css url()/@import 全禁;文本中仅允许虚构域 `internal.example.net`) | test_artifact 断言 |
| 项目→决策→资源→下一行动 关系与点击切换 | 有(内联 JS) | test_artifact + 截图 07 |
| Mermaid 探测 | 保留 ```mermaid 源文本,明确标注"仅用于 Mermaid 能力探测",不加载 CDN | test_artifact 断言 |
| **内嵌 WebView** | **unsupported** | Flet 0.86 标准包无 `ft.WebView` 控件(`dir(flet)` 探测仅有 `WebViewConfiguration` 等无关类型);UI 未伪造内嵌,回退为"摘要 + 路径 + 在浏览器打开"(见截图 01 Artifact 卡与 ai 面板下方说明) |
| 外部打开 | **PASS** | 应用内按钮 → `page.launch_url("file://…/project-flow.html")` 真实代码路径,浏览器成功打开(截图 07);来源项目 ID 与路径在工作台与 Artifact 页两侧均可见 |
| 离线 | **PASS(结构性)** | 页面零外部加载引用(测试断言);应用除 localhost 服务外无网络调用。**物理断网未执行**(避免中断用户本机网络)——如需可手动断网复核,预期不受影响 |

## 9. 分层检查

```bash
grep -rn "import flet|from flet" prototypes/flet_workbench/{domain,runtime,services}
# 无输出(clean)
```

`domain/ runtime/ services/` 零 Flet 依赖;领域规则(停滞判定、Heatmap 聚合、Proposal 权限)全部在 WorkspaceService,UI 回调无复制。

## 10. macOS 结果与 Windows/公司环境未知项

macOS 本机:桌面 PASS、Web PASS、外部 Artifact PASS、离线结构性 PASS。

以下全部记为 `unknown`,不得由本报告推断(需公司环境实测):

- Windows 版本与 Python 3.12 可用性;
- 公司镜像能否提供固定 Flet 0.86.5 及传递依赖;
- Visual Studio Desktop C++ / Flutter 构建工具审批;
- 外部 EXE 禁令是否允许内部编译签名 EXE;若不允许,Flet 动态 Web 资产是否批准;
- localhost 端口与 WebSocket 政策;
- 中文路径、长路径、LocalAppData、文件权限;
- OpenCode `serve`/OpenAPI/SSE/session/permission/MCP/agent 实测;
- Flet/Flutter 运行资产的公司内网批准。

## 11. 推荐结果

**ESCALATE**(依据审查清单 Gate 12 判定规则:仅"Artifact 内嵌不支持"一项不满足,其余可验证项全部通过且未知项如实标注)

需要用户决策的两件事:

1. **是否接受"Artifact 经外部浏览器打开"**——Flet 0.86 标准能力无内嵌 WebView(引入需自定义 Dart/第三方包,已被样片边界排除);
2. **公司 Windows/内网政策**未探测,正式采用前需按第 10 节清单实测。

若用户接受外部浏览器 Artifact 且公司环境探测通过 → 可按清单第 12 节 P1–P8 进入正式实施;若不接受 → 启用第 13 节 React 备用分支(保留全部已验证的 Python domain/runtime/services/tests)。

---

## 附:执行边界自查

- 未修改 `app/`、未修改既有 `tests/`、未读取/改动 `data-issue-vault/` 内容、未恢复已删除的模型路由文件、未安装 Node、未引入 pystray/Quill/更新器/自定义 Dart、未执行破坏性 Git 命令、未提交任何内容(等待用户指示最小提交点)。
- 截图编排使用的 `SPIKE_SCENE` 环境变量钩子仅存在于 `main.py` 组合层(无领域逻辑)。
- 本报告完成后停止,不自行开始正式 `app/` 重构。

## 附:审查后修补记录(2026-08-31)

独立审查归档后,用户上手体验发现节点页"测试资源(Markdown 卡)与相关资源卡右边框不对齐"。像素测量证实:Markdown 卡右边框 x=1860、相关资源卡 x=2297,相差 437px。根因:Flet `Column` 默认不横向拉伸子控件,卡片收缩为内容自然宽度。修复:为各视图与 AI 面板中承载卡片的 `Column` 统一加 `horizontal_alignment=ft.CrossAxisAlignment.STRETCH`(node_detail / project_overview / today / activity / ai_panel)。

- 修复后重测:样片 30 tests OK;节点页两卡边框经像素复测对齐(满宽 850..2329)。
- 证据截图 01/02/03/04 已用修复后版本重捕;05-08 未受该修复影响,维持原捕。
- 分级:P2(显著视觉偏差),非阻塞,已在本轮修复。

### 修补 2:标签改为行内跟随条目(用户反馈)

用户指出参考图中标签应放在文件与相关 action/举措之后,而非独立区块。改动:

- `views/node_detail.py`:资源行文件名后紧跟彩色标签徽章(常用/环境/会议/记录/申请/外部,样式映射 `_TAG_STYLES`);移除独立"标签"卡,"关系"卡满宽。
- `views/project_overview.py`:「当前需要关注」行动条目后紧跟状态徽章(进行中·绿 / 等待·橙 / 待办·灰,`_STATUS_TAG`),替代原"· status"纯文本。
- 合同测试同步更新并先行 RED:`test_tags_follow_resource_files_not_standalone_section`、`test_status_tags_follow_action_rows`;样片全量 **32 tests OK**。
- 证据截图 01/02 已重捕。分级:P2(与批准参考图的结构偏差),非阻塞,已修复。

### 未决问题:大纲行尾 chevron 显示异常 —— 已解决(2026-08-31,接续会话)

用户报告"项目总览的 > 显示不正常"。上一会话的像素取证结论("行尾 81px 宽双重字形簇")**已被推翻**:复核发现当时存档的 `/tmp/ch-*.png` 实为**抓错窗口**的截图(整页零紫色像素、无工作台任何配色,来自其他应用),据此得出的"图标字体渲染异常/字形粘连"诊断不成立。

**接续会话的重新诊断(全部可复现)**:

1. 取证方式:本机 `screencapture` 与 computer-use 均无屏幕录制权限(TCC 拒绝),改用 Flet 0.86.5 内置 `page.take_screenshot()`(需在页面注册前设 `page.enable_screenshots = True`),由应用**自截**桌面客户端原生渲染(2880×1744@2x),零 OS 权限依赖。该钩子已并入 `main.py` 组合层(`SPIKE_SHOT` 环境变量,与既有 `SPIKE_SCENE` 同机制)。
2. 图标本体无缺陷:单变量对照探针显示 `CHEVRON_RIGHT` 及 ROUNDED/SHARP/OUTLINED 变体、`KEYBOARD_ARROW_RIGHT` 等在桌面客户端均渲染为单个干净的 ">"(同一常量 size=20 完全正常),图标字体与客户端映射无问题。
3. **真因:字形墨迹占比**。Material `chevron_right` 的墨迹仅约占字面框 50%,`ft.Icon(..., size=14)` 实际渲染出的 chevron 墨迹仅约 **7×5.5 逻辑像素**(自截实测 w=9 h=14 retina,色彩核心 w7 h11),又以 `text_faint` 灰呈现——在 13px 标题旁就是一颗细小的"渣点",视觉上像渲染损坏。行首图标(flag/group 等)墨迹占比大,故不受影响。

**修复**(RED→GREEN):`components/project_outline.py` 行尾改用文本字形 `ft.Text("›", size=18)`,保留激活紫/非激活灰逻辑;新增合同测试 `test_outline_rows_use_legible_text_chevron`(大纲 7 行行尾必须含 "›" 文本、禁止 CHEVRON 图标)。修复后自截实测:标记墨迹 15 retina 高(约标题墨迹 75%),行内垂直居中,笔画清晰。

- 样片全量 **33 tests OK**(32+1 新增);旧系统 **44/44 OK** 无回归。
- 截图 01/02 已用 `SPIKE_SHOT` 自截重捕(2880×1744 内容区,此前为含边框窗口截屏 2880×1800;方法变更不改变画面内容比例)。
- 分级:P2(显著视觉/交互偏差),已修复;探针脚本(`_probe.py`)为一次性诊断件,已删除。

### 修补 3:捆绑 Noto Sans SC,消除 Windows 字体回落(2026-08-31,公司验证反馈)

公司内网实测:Flet 运行无问题(ESCALATE 第 2 项的 8 项 unknown 中,运行类项已由实测覆盖),但 **Windows 字体不好看**。根因:样片从未设置 font_family(全库 grep 零命中),macOS 回落 SF Pro/苹方,Windows 回落 Segoe UI + 微软雅黑混排。

修复:捆绑 **Noto Sans SC 可变字重字体**(17,772,300 字节,SHA256 `a3041811…99af0da`,来源 google/fonts 官方仓库,OFL 许可可内网分发)至 `prototypes/flet_workbench/fonts/`,见 `fonts/FONT_NOTES.md`;`main.py` 组合层注册 `ft.app(assets_dir="fonts")` + `page.fonts` + `page.theme = ft.Theme(font_family="Workbench")`,全控件生效。

- 验证:macOS 自截对照换字体前后,导航标题字形轮廓实测变化(笔画/字面/横画均不同,字体确已生效);无 tofu、字重层级存在。截图 01–04 已用新字体重捕。
- 局限如实记录:本机仅能 macOS 验证;Windows 渲染因同一字体文件随仓库分发而确定,**观感复验留给公司侧**(git pull 后直接看)。
- 分级:P2(显著视觉偏差),已修复;仓库体量 +17MB(字体文件)。

### 修补 4:全局底部快速记录条(2026-08-31,用户需求)

用户要求"每个页面最下方有输入框"。核实:样片原本**没有**——骨架 `build_page` 只有 导航|内容|AI面板 三列;Today 的"快速记录"是静态摆设(按钮无回调、不写数据)。

实现(RED→GREEN,样片 36→42 tests OK):

- 领域层:`Idea` 模型(pending 初始态)+ `WorkspaceService.quick_capture(text)`(空文本拒绝;唯一豁免 Proposal 边界的写入——用户亲手输入即显式动作)+ `capture_added` 活动事件并计入有意义事件(点亮热力图)。
- UI:`build_page` 底部全局捕获条(回车与"记录"按钮同回调,经 `on_capture` 上交,回调内零领域规则);四页共用骨架天然每页可见;`main.py` 接线后整页重建即清空输入。Today 的"待整理想法"改读 `service.ideas()` 真实数据,移除原静态记录卡。
- 验证:捕获条像素检出(底部白条+边框行 1722+紫色按钮);截图 01–04 含新骨架。
- 旧系统 **44/44 OK** 无回归。

## Addendum 2026-08-31 — 决策与后续增量

本报告原判定 **ESCALATE** 冻结不动。当日用户已作出决策并推进后续工作:

- **ESCALATE 待决项 1(Artifact 外部浏览器打开)**:随本地采用被接受;内嵌 WebView 维持 unsupported。
- **ESCALATE 待决项 2(公司环境)**:公司内网已实测运行样片(见修补 3),Python 3.13 运行兼容性事实上已验证;剩余为审批/分发类事项,移交 COMPANY_ENVIRONMENT_CHECKLIST。
- **决策:Flet 本地/macOS 正式采用**,P1–P8 解冻,以 `docs/plans/2026-08-31-workbench-v2-formalization-adjustment.md` 为准。
- **报告后增量**(未经本报告审查,记录于调整文档):全页可编辑(每日计划/工作记录/项目元数据/行动标题/节点标题/备注/资源)、DayRecord/PlanItem/Resource 模型、plan_updated/worklog_updated 活动种类、`components/editable.py`;样片测试 42 → 69,旧系统 44/44 无回归。

