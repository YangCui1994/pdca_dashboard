# 本地 AI Markdown 工作台方案与 OpenCode 接入排查

## 目标

构建一个个人本地使用的网页输入工具，用于记录和整理：

- 数据异常、数据特征、字段口径疑问
- 个人分析想法
- 临时领导需求
- 跨团队沟通草稿
- 后续可沉淀为知识库、checklist 或开发需求的线索

第一版不追求多人协作和复杂数据库。推荐路线是：

```text
本地网页输入端 -> 本地后端/AI 调用层 -> Markdown 文件夹
```

Markdown 文件作为底层数据，后续可以迁移到 Obsidian 类工具、公司内部 Markdown 管理工具，或再升级成本地看板。

## 当前约束

- 公司内部不能外接 Claude、Codex、ChatGPT 等闭源模型。
- 当前主要通过 OpenCode 命令行使用内部模型。
- 内部模型包括 Deepseek、GLM、Minimax 等。
- OpenCode 配置中可见类似：
  - `BaseURL: aigate.xxxxx.com/v1`
  - models: `Deepseek V4 Flash`、`GLM`、`Minimax`
  - 部分模型支持 `input text image`，`output text`
- 当前希望先个人本地使用。
- 本地可能没有 SQLite，也可能不能安装复杂依赖。
- 当前更倾向于用本地网页作为输入口，保存为 Markdown。
- 电脑环境：
  - Windows
  - 已安装 Git，可使用 Git Bash
  - 可在 VS Code 中使用 Terminal

## 产品判断

仅靠“自己写 Markdown，然后让 AI 做周报”迭代效率不够。更合适的是：

```text
本地网页输入端 + AI 即时整理面板 + Markdown 持久化存档
```

网页负责高频输入、即时追问、沟通草稿生成；Markdown 负责留档、迁移和后续知识沉淀。

## 第一版功能范围

### 输入类型

第一版建议支持 5 类输入：

1. 数据异常/疑点
2. 个人分析想法
3. 临时领导需求
4. 跨团队沟通草稿
5. 词条/口径问题

### 页面结构

建议三栏：

```text
左侧：Inbox 列表
中间：原始输入 + 编辑区
右侧：AI 整理/追问/回复面板
```

### 基础字段

- 标题
- 类型
- 状态
- 优先级
- 相关对象：表、字段、设备、指标、业务场景
- 图片、链接或文件路径
- 原始想法
- AI 整理结果
- 下一步动作
- 保存位置

字段不应全部强制手填。第一版应允许用户先输入自然语言，再由 AI 自动补全字段。

### AI 动作按钮

第一版建议先做固定按钮，而不是泛泛聊天框：

1. 整理成卡片
2. 追问我
3. 生成平台核实问题
4. 生成开发需求草稿
5. 生成领导反馈
6. 非暴力沟通润色
7. 沉淀为知识条目
8. 生成下一步 todo

## 推荐 Markdown 文件夹结构

```text
data-issue-vault/
  00_inbox/
  01_issues/
  02_terms/
  03_checklists/
  04_weekly_reviews/
  05_knowledge/
  99_archive/
    已闭环/
    误报/
```

## 问题卡片模板

```markdown
---
type: issue
status: 新线索
priority: 中
created: 2026-06-03
updated: 2026-06-03
owner: 我
related_terms: []
related_tables: []
related_fields: []
tags: []
---

# 标题

## 一句话描述

## 背景

## 观察到的现象

- 时间范围：
- 涉及对象：
- 涉及指标：
- 实际表现：
- 期望表现：

## 当前判断

## 需要补充的信息

## 给平台同事的核实问题

## 回复与进展

## 最终结论

## 后续沉淀

- 是否加入 checklist：
- 是否转开发需求：
- 是否形成知识库条目：
```

## AI skill/prompt 模板建议

第一版不需要复杂插件系统。可以先把 skill 设计成 prompt 模板文件：

```text
skills/
  issue_card.md
  socratic_review.md
  nvc_reply.md
  platform_question.md
  leader_update.md
  dev_requirement.md
  data_checklist.md
  knowledge_note.md
```

每个按钮对应一个模板。系统把模板和用户输入拼接后发给模型，再把结果展示给用户编辑确认。

## OpenCode 与模型接入判断

当前已知：

- `opencode serve --port 4096` 曾输出：
  - `service=models.dev, error=Unable to connect`
  - `Failed to fetch models.dev`
  - `OPENCODE server listening on http://127.0.0.1:4096`
- `curl -v http://127.0.0.1:4096` 可以 connect，但返回 `unauthorized`

这说明：

1. OpenCode server 本地端口是通的。
2. 当前卡点是鉴权，不是网络连接。
3. 还不能确认 OpenCode server 是否能作为模型 API 代理。
4. 更推荐优先验证 `aigate.xxxxx.com/v1` 是否为 OpenAI-compatible API。

### 推荐接入优先级

```text
优先级 1：本地网页后端 -> aigate.xxxxx.com/v1
优先级 2：本地网页后端 -> OpenCode server 127.0.0.1:4096
优先级 3：网页生成 prompt -> 手动复制到 OpenCode
```

## 给内部 chatbot 的排查提示词

将下面提示词发给内部 chatbot，让它根据实际终端结果继续迭代排查。

```text
你现在扮演一名熟悉 OpenCode、Windows、VS Code Terminal、本地服务、HTTP API、OpenAI-compatible API 的技术顾问。请帮我排查一个本地 AI 工具接入问题。

我的电脑和使用环境：
- 操作系统：Windows
- 我已经安装 Git，因此可以使用 Git Bash
- 我可以在 VS Code 里面打开 Terminal
- 我平时通过命令行使用 OpenCode
- 我希望后续开发一个个人本地网页工具
- 这个工具优先在我自己电脑本地运行，不做团队部署
- 工具最终希望保存 Markdown 文件，形成类似 Obsidian 的本地知识库
- 公司内部不能外接 Claude、Codex、ChatGPT 这类闭源模型
- 公司内部主要使用内部部署的开源模型，例如 Deepseek、GLM、Minimax
- 目前 OpenCode 配置文件里能看到类似：
  - BaseURL: aigate.xxxxx.com/v1
  - models: Deepseek V4 Flash、GLM、Minimax 等
  - 部分模型支持 input text image，output text

我要开发的本地网页工具用途：
1. 记录数据异常、数据特征、字段口径疑问；
2. 记录个人分析想法；
3. 记录临时领导需求；
4. 辅助跨团队沟通；
5. 让 AI 帮我整理碎片输入成 Markdown 问题卡片；
6. 让 AI 生成平台核实问题；
7. 让 AI 生成领导反馈；
8. 让 AI 使用苏格拉底式提问法检查我的想法；
9. 让 AI 使用非暴力沟通方式润色工作回复；
10. 最后把确认后的内容保存到本地 Markdown 文件夹。

我当前已经做过的测试：
我运行过：

opencode serve --port 4096

看到过类似输出：
- service=models.dev, error=Unable to connect
- Failed to fetch models.dev
- Warning: OPENCODE_SERVER_PASSWORD is not set server is unsecured
- OPENCODE server listening on http://127.0.0.1:4096

后来我测试：

curl -v http://127.0.0.1:4096

结果能 connect 到 127.0.0.1:4096，但返回 unauthorized。

这说明：
- OpenCode server 本地端口是通的；
- 但 OpenCode server 需要鉴权；
- 目前还不确定它是否能作为本地网页调用模型的 API 代理。

请你一步步指导我排查。请非常具体地告诉我：
- 在哪里输入命令；
- 使用 VS Code Terminal、PowerShell、CMD、还是 Git Bash；
- 每条命令是什么；
- 看到不同结果分别说明什么；
- 下一步应该怎么做。

请优先使用我可以在 Windows + VS Code Terminal + Git Bash 中执行的命令。

第一部分：确认 OpenCode server 是否真的启动

请先指导我：

1. 打开 VS Code
2. 菜单选择 Terminal / New Terminal
3. 如果可以选择终端类型，优先选择 Git Bash；如果没有，就用 PowerShell
4. 在第一个终端窗口里输入：

OPENCODE_SERVER_PASSWORD=test123 opencode serve --port 4096

如果 PowerShell 不支持这种写法，请告诉我 PowerShell 应该怎么写，例如：

$env:OPENCODE_SERVER_PASSWORD="test123"
opencode serve --port 4096

请提醒我：
- 这个终端窗口不要关闭；
- 如果关闭，OpenCode server 也会停止。

然后请指导我打开第二个 Terminal，测试：

curl -v http://127.0.0.1:4096

请解释：
- 如果 connected 但 unauthorized，说明什么；
- 如果 failed to connect，说明什么；
- 如果返回网页或 JSON，说明什么。

第二部分：确认 OPENCODE_SERVER_PASSWORD 如何传递

请让我在第二个 Terminal 里测试以下几种认证方式，并根据结果判断哪种有效：

1. Bearer token：

curl -v http://127.0.0.1:4096 -H "Authorization: Bearer test123"

2. Basic Auth，用户名为空或任意：

curl -v http://127.0.0.1:4096 -u ":test123"

3. Basic Auth，用户名为 opencode：

curl -v http://127.0.0.1:4096 -u "opencode:test123"

4. 如果 OpenCode 有指定 Header，请告诉我可能是什么，例如：

curl -v http://127.0.0.1:4096 -H "X-OpenCode-Password: test123"

请你指导我如何从 curl -v 的响应头判断认证方式，例如：
- WWW-Authenticate: Basic
- 401 Unauthorized
- 403 Forbidden
- 200 OK
- 404 Not Found

第三部分：确认 OpenCode server 是否有 OpenAI-compatible API

请让我测试以下接口。每个接口都要带上前面确认有效的鉴权方式。

先测试：

curl -v http://127.0.0.1:4096/v1/models

再测试：

curl -v http://127.0.0.1:4096/v1/chat/completions

如果需要 POST，请让我测试：

curl -v http://127.0.0.1:4096/v1/chat/completions ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer test123" ^
  -d "{\"model\":\"这里替换成真实模型id\",\"messages\":[{\"role\":\"user\",\"content\":\"请回复：测试成功\"}],\"temperature\":0.2}"

请注意我是 Windows 用户：
- 如果是 PowerShell，命令换行方式可能不同；
- 如果是 Git Bash，可以用反斜杠 \；
- 请分别告诉我 PowerShell 和 Git Bash 的写法。

请解释：
- /v1/models 返回 200 代表什么；
- 返回 401/403 代表什么；
- 返回 404 代表什么；
- /v1/chat/completions 返回 405 代表什么；
- 如果返回 JSON 但字段不是 OpenAI 格式，说明什么。

第四部分：确认是否应该直接调用 aigate.xxxxx.com/v1

请指导我查看 OpenCode 配置文件里的 BaseURL 和模型 id。请告诉我在 Windows 上可以在哪里找配置文件，例如：
- 用户目录下的 .opencode
- AppData
- .config
- 当前项目目录
- opencode.json

请让我在 VS Code Terminal 里尝试查找配置文件。

Git Bash 可用：

find ~ -iname "*opencode*" 2>/dev/null

PowerShell 可用：

Get-ChildItem -Path $HOME -Recurse -Filter "*opencode*" -ErrorAction SilentlyContinue

然后请指导我测试内部模型网关。

先测试模型列表：

curl -v https://aigate.xxxxx.com/v1/models

如果需要 token：

curl -v https://aigate.xxxxx.com/v1/models -H "Authorization: Bearer 这里替换成token"

再测试 chat completions：

curl -v https://aigate.xxxxx.com/v1/chat/completions ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer 这里替换成token" ^
  -d "{\"model\":\"真实模型id\",\"messages\":[{\"role\":\"user\",\"content\":\"请回复：测试成功\"}],\"temperature\":0.2}"

请你解释：
- 返回 200：说明什么；
- 返回 401：说明什么；
- 返回 403：说明什么；
- 返回 404：说明什么；
- Failed to connect：说明什么；
- Could not resolve host：说明什么；
- SSL certificate problem：说明什么；
- 只访问 /v1 没结果但 /v1/models 有结果，说明什么。

第五部分：判断 model id 和 token 从哪里来

请帮我确认：
1. opencode.json 里的模型显示名和 API model id 是否可能不同；
2. 应该优先使用哪个字段作为 curl 的 model；
3. token 是否可能在：
   - opencode.json
   - 环境变量
   - 公司统一登录系统
   - OpenCode provider 配置
   - Windows Credential Manager
4. 如何在 Windows 终端查看环境变量。

PowerShell：

Get-ChildItem Env: | Select-String -Pattern "OPENAI|OPENCODE|AIGATE|API|TOKEN|KEY|MODEL|DEEPSEEK|GLM|MINIMAX"

Git Bash：

env | grep -Ei "OPENAI|OPENCODE|AIGATE|API|TOKEN|KEY|MODEL|DEEPSEEK|GLM|MINIMAX"

第六部分：最终请给我明确结论

请你在排查结束后，用下面格式给我最终答案：

【结论】
- 推荐路径：A 直接调用 aigate.xxxxx.com/v1 / B 调用 OpenCode server 127.0.0.1:4096 / C 暂时只能手动复制 prompt 到 OpenCode
- 推荐原因：
- 是否确认 OpenAI-compatible：
- 可用 endpoint：
- 鉴权方式：
- 可用 model id：
- 是否支持图片输入：
- 是否存在 CORS 风险：
- 本地网页是否需要本地后端代理：
- 如果 AI API 暂时不通，降级方案是什么：

【本地网页建议架构】
- 前端：
- 后端：
- AI 调用：
- Markdown 保存：
- 配置文件：
- 未来扩展：

【我还需要补充的信息】
请列出仍然缺失的信息，不要超过 8 条。

请注意：
- 不要让我暴露真实 token。
- 不要让我贴公司内部完整域名。
- 不要让我贴敏感配置。
- 如果我需要把结果转述给其他 AI，请告诉我哪些信息可以脱敏后转述。
- 请避免泛泛解释，每一步都要给出可执行命令和判断标准。
```

## 后续实现建议

当模型接入方式确认后，优先实现：

1. 本地网页输入框
2. 类型选择：异常、想法、领导需求、沟通草稿、词条
3. 图片/链接/文件路径输入
4. AI 动作按钮
5. AI 输出编辑区
6. 一键保存 Markdown
7. 本地 Markdown 列表与筛选

如果 AI API 暂时不通，第一版仍可实现：

```text
网页生成结构化 prompt -> 用户复制到 OpenCode -> 粘贴 AI 结果 -> 保存 Markdown
```

这保证项目不会被模型接口排查卡死。
