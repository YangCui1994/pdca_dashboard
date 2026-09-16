# 个人工作台 v2 · 使用与迁移指南

更新:2026-09-16(UX 原型合并版:默认网页模式、TodayHub、项目页 master-detail、entp-manual 配色)。
对应代码:`workbench/`(Flet 0.86.5,Python 3.12+,纯标准库 + flet)。
计划与决策:`docs/plans/2026-09-15-merge-ux-prototypes.md`;UI 风格基准:`refs/SOURCES.md`。

## 1. 启动

```bash
cd pdca_dashboard
.venv/bin/python -m workbench.main                      # 网页模式(默认),演示数据,http://127.0.0.1:8550
.venv/bin/python -m workbench.main --vault data-issue-vault/v2   # 真实数据,编辑落盘
.venv/bin/python -m workbench.main --ui desktop         # 退回桌面窗口
```

首次用真实 vault 启动会写入一套演示工作区作起点,删掉演示项目即可换成自己的。

常用参数:

| 参数 | 作用 |
|---|---|
| `--ui web \| desktop` | 运行形态,默认 **web**(浏览器访问;公司内网部署形态) |
| `--host <地址>` | web 监听地址,默认 `127.0.0.1`;公司部署在办公机/服务器用 `0.0.0.0` |
| `--port <端口>` | web 端口,默认 8550 |
| `--watch-dir <目录>` | 监听目录:新 .md/.txt 经 file_route 自动归档到项目进度(高置信自动写入可一键撤销,低置信只提示不写入);缺省不监听 |
| `--vault <目录>` | 数据目录;不指定则内存演示(永不写真实数据) |
| `--provider fake \| openai` | AI runtime,默认 fake(离线演示) |
| `--ai-base-url <url>` | OpenAI 兼容端点,如 `http://127.0.0.1:4096/v1` |
| `--ai-model <名>` | 模型名 |
| `--ai-api-key <key>` | 可选;也可用环境变量 `WORKBENCH_AI_BASE_URL / _MODEL / _API_KEY` |

网页模式注意事项:无认证,仅限内网可信环境;多个浏览器会话共享同一 vault,并发写会判 StorageConflict——首版按"单人使用、多端查看"定位。

## 2. 日常使用

- **今天页(TodayHub)**:顶部常驻智能捕获条,`!文字`=直接进今日计划、`#项目名 文字`=归属该项目的计划、纯文字=待整理想法;回车提交后清空+焦点回归。昨日有未完成时出现顺延条:[顺延到今天](整批可撤销)、[昨日收尾向导];昨天写过 Check/Act 会显示「昨日已收尾 ✓」。待整理想法每行 [入今日][保留][归档][思考方式▾],上下方向键可移动选择高亮。
- **编辑**:所有文本双击进入编辑。单行回车/失焦提交;工作记录与节点备注是多行编辑器,保存/取消按钮提交。计划项 CLOSE 删除可从 snackbar 撤销。
- **昨日收尾向导**:四步(勾完成 → Check 引导 → 未完成逐条处置 → Act),AI 只出草稿,可改可跳过;Check/Act 落当天记录。
- **AI 草稿卡**:「整理今日上下文」卡的 生成整理建议 / Check 引导 / 本周复盘,以及思考方式,产出统一草稿卡(采纳/改后采纳/忽略);AI 失败不出卡。红线:AI 只产草稿,采纳才写盘(唯一例外:`--watch-dir` 高置信自动追加,带撤销)。
- **项目页(master-detail)**:左 1/4 项目紧凑卡列表(名称+元信息+停滞红标),点击切换右侧详情;右 3/4 = 可编辑元信息 + 大纲 + 行动列表(状态色块点按循环直改)+ 真实停滞天数 + 14 天活动。
- **想法页**:想法只有状态流转(待整理→已保留→已归档),**原文不可改写**(数据契约)。
- **AI 审查**:项目详情右侧「运行项目审查」→ 流式过程 → 待确认 Proposal → 确认后才改正式状态。AI 调用全部在后台线程,真实端点不冻结界面。
- **新建项目**:项目首页「＋ 新建项目」卡片,创建后直接进入。

## 3. 数据布局(vault 目录)

```
<vault>/
  workspace.json                       # 清单:每个受保护文件的 revision + 内容哈希
  ideas.json                           # 想法(原文只增不改)
  activity.jsonl                       # 活动事件追加日志(热力图/停滞判定数据源)
  days/2026-09-01.json                 # 当日计划条目(结构化)
  days/2026-09-01.md                   # 当日工作记录(叙事 Markdown)
  projects/<pid>/project.json          # 项目元数据 + 行动清单
  projects/<pid>/nodes/<nid>.json      # 节点标题/类型/资源卡
  projects/<pid>/nodes/<nid>.md        # 节点备注(叙事 Markdown)
```

分工原则:**叙事进 Markdown,结构化状态进 JSON**;两者由应用配对维护。

## 4. 数据整理守则

1. **优先在应用里改**。应用写文件会同步更新 `workspace.json` 的哈希。
2. **手改文件会被拦下**:直接编辑受保护文件后,应用内再保存会报 `StorageConflict`(拒绝覆盖你的手改)。处理:手改内容想保留→以磁盘为准,重启应用;想丢弃手改→用应用重写一遍。`activity.jsonl` 例外,它是只追加的日志。
3. **不要手改 ID**(项目/节点/行动/资源/计划条目),它们是文件名和关联键。
4. **备份 = 拷贝整个 vault 目录**。单文件恢复也行,但记得同时拷 `workspace.json`。
5. 真实数据永远不进 git(`data-issue-vault/**/*` 已被 ignore,仓库只保留 `.gitkeep` 骨架)。

## 5. 迁移到公司环境

前置事实:公司内网已实测运行过本应用(2026-08-31 字体验证),Python 为 3.13,本机为 3.12——两者都在 flet 0.86.5 支持范围。

1. **代码**:公司机器 `git clone` / `git pull` 本仓库。
2. **依赖**:
   ```bash
   python3 -m venv .venv
   .venv/bin/python -m pip install -r workbench/requirements.txt   # flet[all]==0.86.5
   ```
   内网镜像没有该包时,在可上网机器 `pip download 'flet[all]==0.86.5' -d wheels/` 打包 wheelhouse 随仓库携带,公司侧 `pip install --no-index --find-links wheels/ ...`。
3. **网页模式(默认)**:公司部署在办公机/服务器上跑 `--host 0.0.0.0`,同事浏览器访问 `http://<host>:8550`。web 形态无桌面客户端依赖,离线机器也免分发 Flet client。桌面模式才需要 `~/.flet/client/` 离线宿主(`--ui desktop`)。
4. **数据**:整目录拷贝 `<vault>`(默认 `data-issue-vault/v2/`),或随私有 git 仓之外用网盘/U 盘。旧 v1 数据(任务文件夹)先不动,v2 达到日常可用后走 P4′「显式导入」(预览→确认→复制)。
5. **AI**:`opencode serve --port 4096` 后 `--provider openai --ai-base-url http://127.0.0.1:4096/v1 --ai-model <名>`;或内网 aigate 的 `/v1`。密钥放环境变量,不写进仓库。
6. **验证清单**:启动、建项目、编辑计划/工作记录、关闭重开确认落盘、AI 审查一轮、断网跑一遍以上。

## 6. GitHub 与备份

- 远端:`git@github.com:YangCui1994/pdca_dashboard.git`,日常 `git push origin workbench-mvp`。
- 仓库只含代码/文档/演示 fixture 与捆绑字体;真实工作数据、`.venv`、本地工具目录均已 ignore。
- 建议节奏:功能增量合入后推送;数据备份另行拷 vault 目录(两者独立)。

## 7. 故障排查

| 现象 | 处理 |
|---|---|
| 保存时报 StorageConflict | 文件被外部改过;决定保留哪份(见第 4 节第 2 条) |
| AI 面板橙色「运行失败」 | 端点/模型/网络问题;检查 `--ai-*` 参数与服务是否在跑 |
| 窗口字体异常 | 全局字体为 Microsoft YaHei UI(entp-manual 基准);Windows 自带该字体,确认系统字体未被裁剪 |
| Python 版本不符 | 3.12/3.13 均可;不要用 3.10 及以下 |
| 数据看起来丢了 | 确认启动时带了 `--vault`;演示模式不落盘 |
