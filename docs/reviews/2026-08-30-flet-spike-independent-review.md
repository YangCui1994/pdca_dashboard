# Flet Spike Independent Review(独立审查结论归档)

- 审查日期:2026-08-30
- Verdict:**ESCALATE**
- 审查者路由:GLM 独立审查会话(与实施会话分离),模型 `glm-5.3[1m]`,effort `unknown`
- 被审对象:`prototypes/flet_workbench/`、`docs/decisions/FLET_FEASIBILITY_REPORT.md` 及测试/截图证据
- 本文档由根协调会话代为归档(审查者全程只读,未修改任何文件)

## 逐 Gate 结论

| Gate | 结论 | 关键证据 |
|---|---|---|
| 0 Git/数据安全 | PASS | 用户 7 项改动与 baseline 逐行一致;diff 仅用户改动;vault 3 忽略条目未读;密钥/真实域名/真实路径扫描零命中(`workbench.com` 为模块路径误报) |
| 1 旧系统基线 | PASS | 44/44 OK(审查者独立重跑) |
| 2 依赖/分层 | PASS | requirements 固定 0.86.5;核心层零 flet import(独立重跑 grep);main.py 仅组合,规则集中于 WorkspaceService(main.py:99-107 回调一行转发) |
| 3 TDD/行为 | PASS | 30/30 OK(独立重跑);清单 7.2 十项行为逐条读测试代码核实;C3 拒绝首跑即绿等流程偏差已如实记录,关键权限边界有真实测试 → 记流程偏差,不 BLOCK |
| 4 UI 合同/视觉 | PASS | 8 张截图 vs 2 张参考图逐项对照;无 P0/P1/P2;报告 P3 清单属实 |
| 5 Fake Runtime/UI 响应 | PASS | page.run_task 异步消费(main.py:74);截图 05 流式中+节点切换;审查者独立运行时探查:接受后仅 act-003 waiting→in_progress、Activity +1,其余字段逐一未变 |
| 6 Artifact | PASS(外开)/ **unsupported(内嵌)** | 审查者独立探测 `hasattr(flet,'WebView')==False`;HTML 151 行全读零外部引用;外开走 launch_url 固定常量路径;离线为结构性 PASS 且报告如实标注物理断网未执行 |
| 7 桌面/Web | PASS | `flet --help`/`flet run --help` 参数实测存在;Web 仅 127.0.0.1(lsof 记录);报告未声称 Windows EXE 或公司批准 |

## Gate 8 决策评分表

| 指标 | 结果 | 证据 |
|---|---|---|
| UI 还原 | PASS(无 P0/P1/P2) | 截图 01-08 vs approved-ui |
| 项目大纲 | PASS | 截图 01/02;outline on_click;UI 合同测试 |
| Fake 流式面板 | PASS | 104 事件 0.000s;截图 05;main.py:74-93 |
| Proposal 边界 | PASS | test_workspace_service:19-42;审查者独立字段级探查 |
| Heatmap | PASS | test_workspace_service:101-128;截图 04 |
| Artifact 外部打开 | PASS(离线结构性) | 截图 07;test_artifact;报告如实标注 |
| Artifact 内嵌 | **unsupported** | 独立探测无 ft.WebView;artifact_panel.py:68 未伪造 |
| 桌面模式 | PASS | 报告第 4 节 + 截图 01-07 |
| 动态 Web | PASS | lsof 127.0.0.1 记录 + 截图 08;CLI 参数实测 |
| 分层 | PASS | grep 零输出;组合层无业务规则 |
| 公司 Windows | 待验证(unknown) | 报告第 10 节 8 项如实列出 |

判定规则:数据安全/Proposal/分层/外部 Artifact 全过;唯一不满足项为"Artifact 内嵌" → **ESCALATE**(与实施者自荐结论一致)。

## Blocking findings

无。

## 需要用户决策

1. 是否接受"Artifact 经外部浏览器打开"作为正式形态(Flet 0.86.5 标准包确无内嵌 WebView,本审查独立证实;不接受则启用实施清单第 13 节 React 备用分支,已验证的 Python domain/runtime/services/tests 全部保留)。
2. 公司 Windows/内网 8 项未知项(报告第 10 节)需在正式采用前实测,尤其 EXE 禁令、Flet 依赖镜像、localhost/WebSocket 政策。

## 附注(非阻塞,P3)

- TDD 的 RED 过程证据仅存于实施会话记录,仓库未归档(实施者按提交边界未 commit)。
- 截图 07 浏览器地址栏含本机真实绝对路径(含用户名),对外分享 docs 前建议裁剪。
- FakeRuntime 对非默认项目生成 Proposal 时硬编码 `act-003`(样片固定 proj-atlas,不影响现有行为)。

## 审查轮次

- full review count:1
- targeted recheck count:0
- new evidence produced:yes(WebView 控件独立探测、接受后字段级运行时探查、flet CLI 参数实测)

## 建议下一步

request user Flet decision(两项决策均接受 → 按实施清单第 12 节 P1–P8 推进)。
