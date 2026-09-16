# Handoff — 公司内网环境验证(Windows)

交接日期:2026-08-31 · 交接对象:公司内网 AI 模型(只读验证角色)

## 0. 一句话任务

在公司 Windows 机器上按 `docs/decisions/COMPANY_ENVIRONMENT_CHECKLIST.md` 逐项实测 Personal Workbench v2 的 Flet 技术样片,按模板出报告。**你只做环境验证,不开发、不改代码、不做架构决策。**

## 1. 项目现状(30 秒版)

- 本仓库是本地优先 PDCA 工作台。`app/` 是已上线的旧原型(44 tests 全过,勿动)。
- `prototypes/flet_workbench/` 是 v2 的 **Flet 技术样片**:虚构数据、FakeRuntime、内存态 WorkspaceService——**它是可完整运行的环境验证品,不是正式产品**。正式 v2(清单 P1–P8)尚未开始,且在等用户的两项 ESCALATE 决策。
- macOS 侧已全部验证通过:桌面/Web 双模式、33 项测试、8 张证据截图、独立审查结论 **ESCALATE**(唯一阻塞项:Artifact 内嵌 WebView 不支持,退化为外部浏览器打开;以及公司环境 8 项 unknown——即你的任务)。
- 全部证据与结论见 `docs/decisions/FLET_FEASIBILITY_REPORT.md`(必读,含 2026-08-31 三轮修补记录)。

## 2. 2026-08-31 会话摘要(交接会话)

1. 闭环了遗留的"大纲行尾 chevron 显示异常":推翻上一会话基于错误截图(抓错窗口)的"字形粘连"诊断;真因是 Material `chevron_right` 墨迹仅占字面框约 50%,`size=14` 实际渲染约 7 逻辑像素。修复:行尾改 `ft.Text("›")`,新增合同测试,样片 33/33、旧系统 44/44。
2. 取证方式变更:发现 Flet 0.86.5 内置 `page.take_screenshot()`,应用可自截原生渲染,不依赖 OS 屏幕录制权限;钩子在 `main.py` 组合层(`SPIKE_SHOT` 环境变量)。
3. 修正 `prototypes/flet_workbench/DEPENDENCY_NOTES.md` 事实错误:桌面宿主 Flet.app(约 134MB)**不随 pip wheel 分发**,首次桌面启动需联网下载到 `~/.flet/client/`;离线内网须预分发并设 `FLET_VIEW_PATH`。Web 模式无此依赖——**因此清单以 Web 模式为主验证路径**。
4. 本 handoff 与 `COMPANY_ENVIRONMENT_CHECKLIST.md` 为本次新增。

## 3. 必读文件(按序)

1. `AGENTS.md`(仓库规则)
2. 本文档
3. `docs/decisions/COMPANY_ENVIRONMENT_CHECKLIST.md`(你的执行清单)
4. `docs/decisions/FLET_FEASIBILITY_REPORT.md`(背景与已验证结论)
5. `prototypes/flet_workbench/DEPENDENCY_NOTES.md`(依赖事实)

## 4. 硬边界(违反任何一条即停止并报告)

- **只读验证**:不修改 `app/`、`prototypes/`、`tests/` 的任何代码;唯一允许的写入是清单要求的报告文件。
- 不读取、不复制真实 `data-issue-vault/` 内容(克隆里本就不含它,被 `.gitignore` 排除)。
- 不安装 Node.js/React,不引入数据库、Quill、托盘、自动更新器、自定义 Dart 扩展。
- 不执行破坏性 Git 命令,不推送、不合并。
- 不把任何密钥、证书、内部 API 地址写入仓库或报告。
- 验证结果只写 `PASS / BLOCK / unknown`,**未实测的一律 `unknown`,禁止推断**。

## 5. 执行与汇报

- 按清单从 D1 开始逐项执行,命令已在清单给出(Windows PowerShell 版)。
- 全部执行完后,把 `docs/decisions/COMPANY_ENVIRONMENT_CHECKLIST.md` 末尾的报告模板填好,保存为 `docs/reviews/company-env-verification-report.md`(新建文件,这是你唯一的新增产物)。
- 停止条件:遇到需要公司 IT/安全部门人工审批的项,标 `unknown` 并在报告中列出"需人工确认问题清单",不要自行绕过。

## 6. Suggested skills(若你的运行环境提供)

- `diagnose`:若某项检查失败且原因不明,按"复现→最小化→假设→取证"循环定位,不要猜测。
- `handoff`:若你的会话上下文耗尽需要中断,用同样的格式把进度交接给下一个会话。

环境没有这些技能时,按清单字面执行即可,不阻塞。

## 7. 速查事实

| 项 | 值 |
|---|---|
| Python | 3.12.x 要求(开发机为 3.12.13) |
| Flet | 0.86.5(`flet[all]`,含 flet/flet-cli/flet-web/flet-desktop 同版本) |
| 样片测试 | 33 项(命令见清单) |
| 旧系统测试 | 44 项(环境验证无需跑,仅在怀疑仓库损坏时跑) |
| Web 模式端口 | 127.0.0.1:8791(只绑回环) |
| 证据截图 | `docs/decisions/assets/flet-spike/01–08`(macOS 采集,供对照) |
