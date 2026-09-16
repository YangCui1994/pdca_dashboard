# 公司内网环境验证清单 — Flet 样片(Windows)

执行者:公司内网 AI 模型 · 依据:`docs/handoffs/2026-08-31-company-environment-verification.md` · 日期:____

填写规则:每项只能填 `PASS / BLOCK / unknown`,附命令输出摘要作证据;未实测一律 `unknown`,禁止推断。唯一下降路径:D 项(一票否决级)全 PASS 才算环境验证通过。

---

## D1 — Python 3.12 可用性【一票否决】

检查:公司机器能否获得 Python 3.12.x。

```powershell
py -3.12 --version
# 或
python --version
```

通过标准:输出 3.12.x。若无安装权限,记录 IT 申请路径后标 `BLOCK`。
结果:____ 证据:____

## D2 — 依赖可安装(内网镜像/离线 wheel)【一票否决】

检查:公司 pip 镜像能否提供 `flet[all]==0.86.5` 及传递依赖。

```powershell
cd <仓库根目录>
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install "flet[all]==0.86.5" -i <公司镜像URL>
.venv\Scripts\python -m pip freeze
```

通过标准:安装成功且 `pip freeze` 完整(留输出作报告附录,供 IT 做白名单)。
镜像缺失时:改用离线 wheel 目录 `pip install --no-index --find-links <wheel目录> -r prototypes/flet_workbench/requirements.txt` 再试;仍失败 → `BLOCK` 并记录缺失包名。
结果:____ 证据:____

## D3 — localhost 端口与 WebSocket【一票否决】

检查:本机回环 TCP + WebSocket 是否被 EDR/组策略禁止。

```powershell
# 起样片 Web 模式(只绑回环)
.venv\Scripts\flet run --web -m prototypes.flet_workbench.main -p 8791 --host 127.0.0.1
# 另开窗口验证监听地址
netstat -ano | findstr 8791
```

通过标准:浏览器访问 `http://127.0.0.1:8791` 出现工作台界面(左侧导航"今天/想法/项目/活动/归档");`netstat` 显示仅 `127.0.0.1:8791` 监听(不得 `0.0.0.0`);页面能交互即隐含 WebSocket 通(界面刷新依赖 WS)。
注意事项:公司强制代理时确认 localhost 已绕行(浏览器 no_proxy/例外列表)。
结果:____ 证据:____

## D4 — 样片全量行为冒烟【一票否决】

检查:代码在公司 Windows 上行为一致。

```powershell
.venv\Scripts\python -m unittest discover -s prototypes/flet_workbench/tests -p "test_*.py" -v
```

通过标准:**33 项全部 OK**。随后浏览器内过 8 个场景:项目总览(大纲行尾应有清晰"›"箭头)→ 点击大纲任一节点进节点详情 → Today(计划勾选)→ Activity(热力图点日期)→ 右侧 AI 面板"运行项目审查"(流式事件滚动、完成后出现待确认 Proposal,确认/暂不均可用)→ Artifact 卡"在浏览器打开"。
测试失败:完整粘贴失败用例名与断言,标 `BLOCK`。
结果:____ 证据:____

---

## S1 — 桌面形态离线客户端(仅当需要桌面窗口形态)

背景:桌面宿主 Flet.app(约 134MB)不随 pip wheel 分发,首跑联网下载(见 `prototypes/flet_workbench/DEPENDENCY_NOTES.md`)。离线内网需从有外网的机器复制 `%USERPROFILE%\.flet\client\flet-desktop-full-0.86.5\`,并设 `FLET_VIEW_PATH` 指向本机客户端后运行 `.venv\Scripts\python -m prototypes.flet_workbench.main`。
通过标准:桌面窗口打开且 D4 场景同样可过。Web 形态已足够时本项可标 `不适用`。
结果:____ 证据:____

## S2 — 中文用户名 / 长路径

检查:`%USERNAME%` 含中文或仓库路径较深时,克隆、venv、运行是否正常。

```powershell
git config --global core.longpaths true
git clone -b workbench-mvp <仓库地址> C:\code\pdca   # 建议短 ASCII 路径
echo %USERNAME%
```

通过标准:克隆+D2–D4 全流程无路径错误。若中文用户名导致 `~/.flet` 或 venv 故障,记录具体报错。
结果:____ 证据:____

## S3 — Artifact 外部打开(file:// 协议)

检查:工作台内点"在浏览器打开"能以 `file://` 打开本地 `project-flow.html`,断网状态下节点仍可点击切换详情。
通过标准:浏览器成功打开且交互正常;若安全策略禁 file://,记录 `BLOCK`(影响 ESCALATE 第 1 项决策)。
结果:____ 证据:____

## F1 — 正式版才需要的项(本轮只记录,不实测)

- OpenCode `serve`/SSE/session/permission/MCP/agent 能力探测:____
- 内部模型 API 的证书/代理/密钥位置(密钥不写入任何文件):____
- 若未来发 EXE:VS C++ 构建工具审批、代码签名、SmartScreen/EDR 误报:____

---

## 报告模板(填好后另存为 `docs/reviews/company-env-verification-report.md`)

```text
# 公司环境验证报告(Windows)

日期 / 机器 / Windows 版本 / Python 版本 / Flet 版本:
执行模型(可见标识,不可见写 unknown):

| 项 | 结果 | 证据摘要 |
|---|---|---|
| D1 Python 3.12 | | |
| D2 依赖安装 | | |
| D3 localhost/WS | | |
| D4 冒烟 33 tests + 8 场景 | | |
| S1 桌面离线客户端 | | |
| S2 中文路径/长路径 | | |
| S3 file:// Artifact | | |
| F1 正式版未知项 | | |

总判定:PASS(全部 D 项通过)/ BLOCK(列出一票否决项)/ unknown

需人工确认问题(IT/安全部门):
1. ...

附录:pip freeze 输出
```
