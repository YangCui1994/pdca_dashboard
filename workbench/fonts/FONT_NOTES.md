# Font Notes — 捆绑字体

## 2026-09-16 状态:entp-manual 基准

- 全局字体改为 **Microsoft YaHei UI**(`main.py`: `ft.Theme(font_family="Microsoft YaHei UI")`),
  与用户指定的 entp-manual 风格基准一致(对照表 `refs/SOURCES.md`)。部署目标为公司 Windows
  内网,系统自带该字体。
- 捆绑的 NotoSansSC-VF.ttf 仍随 `assets_dir="fonts"` 注册(`page.fonts`),作为跨平台/离线兜底;
  当前主题字体不引用它。要恢复全捆绑渲染,把 theme font_family 改回 "Workbench" 即可。

## 文件

- `NotoSansSC-VF.ttf`(17,772,300 字节):Noto Sans SC 可变字重字体(100–900 全字重,单文件)
- SHA256:`a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da`

## 来源与许可

- 来源:Google Fonts 官方仓库 `github.com/google/fonts`,路径 `ofl/notosanssc/NotoSansSC[wght].ttf`(2026-08-31 下载)
- 许可:SIL Open Font License 1.1(OFL)——可商用、可内网再分发、可随仓库打包分发

## 为什么捆绑

- 样片此前未设置任何 font_family:macOS 回落 SF Pro/苹方(好看),Windows 回落 Segoe UI + 微软雅黑混排(用户报告"不好看")的根因。
- 捆绑后 macOS/Windows/公司内网渲染完全一致,且离线可用(不依赖系统字体与网络)。
- 在 `main.py` 组合层注册:`ft.app(main, assets_dir="fonts")` + `page.fonts = {"Workbench": "/NotoSansSC-VF.ttf"}` + `page.theme = ft.Theme(font_family="Workbench")`,全控件生效。

## 维护注意

- 升级字体时替换文件并更新本文件的字节数与 SHA256。
- 若未来需要压缩体量,可做子集化(按实际用字),但需重新验证覆盖完整中文常用字。
