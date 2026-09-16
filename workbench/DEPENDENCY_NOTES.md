# Dependency Notes — Flet Spike

记录日期:2026-08-30。本文件记录 Personal Workbench v2 Flet 技术样片的依赖事实。

## 版本

- Python:3.12.13(仓库内 `.venv`,由 `python3.12 -m venv .venv` 创建)
- Flet:0.86.5(含 `flet`、`flet-cli`、`flet-desktop`、`flet-web` 均为 0.86.5)
- pip:26.2.1
- 传递依赖由 `pip install 'flet[all]==0.86.5'` 解析,未另行固定

## 安装来源

- 来源:公共 PyPI(`pypi.org`),安装命令见 `requirements.txt`
- 安装机器:用户本机 macOS(Darwin 24.6.0)
- 该依赖尚未获得公司内网批准;公司镜像是否可提供固定 Flet 及传递依赖:未知(`unknown`)

## Flet/Flutter 运行资产

- `flet` Python 包含 UI 控件定义;`flet-web` 包自带 Web 模式所需的 Flutter 编译资产(随 wheel 分发,离线可用)
- **桌面宿主 Flet.app(约 134MB)不随 wheel 分发**:pip 内 `flet_desktop` 包仅约 44KB 引导代码,首次以桌面模式启动时从网络下载到 `~/.flet/client/flet-desktop-full-<version>/`(2026-08-31 实测修正;本机 macOS 已下载,故样片可直接运行)
- 内网离线环境运行桌面模式,必须预分发该客户端目录并设置 `FLET_VIEW_PATH` 指向本机 Flet.app;Web 模式无此依赖
- 本样片未执行 `flet build`、未生成平台安装包、未触碰系统级 Flutter/Dart 工具链

## 明确未引入

- 未安装 Node.js / npm / React / Vite / FastAPI 应用代码(fastapi 仅作为 flet CLI 的传递依赖安装,样片代码不使用)
- 未安装 pystray(托盘)、自动更新器、Inno Setup
- 未使用 Quill 富文本编辑器
- 未编写自定义 Dart/Flutter 控件,未自定义 Flet 客户端

## 审批状态

- 公司内网批准状态:未提交审批,未知
- 若正式采用,需按公司流程补审 Flet/Flutter 运行资产与桌面打包链
