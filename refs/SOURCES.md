# 参考资料来源清单

## entp-manual（workbench v2 UI 风格基准）

- 来源：https://github.com/TANGuoGUO/entp-manual
- 本地：`refs/entp-manual/`（shallow clone）
- Commit：`e03393eaaa151300c3cb69bbfb96044a2edf3b16`（2026-08-22）
- 访问/下载日期：2026-09-16
- 用途：用户指定——workbench 合并版（v2）的**字体与颜色**以此项目为准。
  注意：这覆盖原计划 §1 的"紫色主题 #6C5CE7"决策；合并执行时 THEME 改按下方色板。

## 风格要点（出处 refs/entp-manual/flet_app.py:80-93, 502-530, 527, 4931）

色板（浅色模式，无暗色）：

| 语义 | 值 |
|---|---|
| 主色 BLUE | `#316BEE`（深 `#2457CC`，软底 `#EEF3FF`） |
| 正文 INK | `#171A21` |
| 次要文字 MUTED | `#737986`（变体 `#515762`/`#555B66`/`#6F7682`） |
| 边框 LINE | `#E7E9EE` |
| 卡片 SURFACE | `#FFFFFF` |
| 侧栏 SIDEBAR | `#F7F8FB` |
| 页面画布 CANVAS | `#FBFCFE` |
| 完成/进行 GREEN | `#37A46A`（软底 `#EAF7EF`） |
| 等待 AMBER | `#B87818`（软底 `#FFF6DF`，深字 `#59451D`） |
| 停滞/错误 RED | `#E45959` |
| 错误 snackbar 底 | `#3A2530`；成功提示底 `#254D38` |
| 中性 pill 底 | `#F1F2F5` / `#F0F1F4` / `#F4F6F9` 等 |

字体与形态：

- 全局 `font_family="Microsoft YaHei UI"`（flet_app.py:527）；代码/等宽用 Consolas（height=1.45，:4931）
- `ThemeMode.LIGHT`、`color_scheme_seed=BLUE`、`VisualDensity.COMFORTABLE`（:502,525-529）
- 正文尺寸 13/14，导航未选中 14 W500；强调色对用"深字+软底"双色组合
