# Infinite Canvas · 个人维护版

基于 [hero8152 / Infinite-Canvas](https://github.com/hero8152/Infinite-Canvas) 的本地修改版本。原作者为 hero8152（Daniel8152）。本仓库整理现有修改，便于在自己的多台电脑上继续维护和更新；不是原作者的官方发布。

维护仓库：[LuoJia00/cs1.1](https://github.com/LuoJia00/cs1.1)。

保留原项目的 [LICENSE](LICENSE)。其中要求二次开发保持开源并注明来源作者，并限制商业用途；本仓库没有改换许可证。

## Windows 第一次使用

1. 用 GitHub Desktop 克隆本仓库，建议放到 `D:\Infinite-Canvas`。
2. 安装 Python 3.10 或更高版本，再双击 `安装依赖.bat`。脚本会创建本项目独立的 `.venv` 并安装依赖。
3. 双击 `启动服务.bat`，浏览器访问 `http://127.0.0.1:3000/`。
4. 在程序中填写自己的 API 配置；按需安装并登录外部 CLI。

如果已有可运行的 Windows 整包，也可以单独复制其中的 `python` 文件夹过来。该环境不由 Git 管理。依赖锁定清单来自当前可运行的 Windows / Python 3.10 环境；其他系统仍需实际安装验证。

macOS 可执行 `python3 -m venv .venv`，然后 `.venv/bin/python -m pip install -r requirements-lock.txt`；使用现有 mac 启动脚本。Windows 自带的 `python` 文件夹不能在 macOS 使用。

## 多电脑更新

开始修改前：关闭服务 → GitHub Desktop 中 Fetch origin → 有更新时 Pull origin → 启动服务。

修改完成后：查看 Changes → 填写修改说明 → Commit to main → Push origin。

如依赖清单更新，先重新运行 `安装依赖.bat`。如果本地修改与远端发生冲突，先保留本地提交，在 Desktop 中解决冲突；不要强制覆盖。

原作者的在线覆盖更新已停用，避免替换此维护版。版本更新统一通过 Git 获取，包括工具、工作流和依赖文件。

## 什么会同步

- 程序代码、网页、程序内置界面资源、工作流、安装脚本及使用说明。
- 不同步 API 密钥、个人配置、生成图片、视频、画布、聊天记录、日志和 Python 环境。
- `static/runninghub` 中运行时保存的个人服务商配置、模型缓存和缩略图也已排除。

`.gitignore` 使用根目录白名单。以后新增根目录文件时，需要明确加入白名单；已有代码目录内的新文件通常会被 Git 发现。

可选：关闭服务后，运行 `迁移配置.bat` 私下导出或导入 API 与提示词等个人配置。生成的 `.private-transfer` 不会上传，配置包未加密且可能含密钥。它不包含聊天、图片、画布、浏览器本地设置、电脑绝对路径或外部工具登录。

完整步骤见 [GitHub多电脑使用教程.md](GitHub多电脑使用教程.md)。提交前可运行 `python tools/repository_check.py` 检查 Git 暂存区的敏感文件、已知密钥和大文件。
