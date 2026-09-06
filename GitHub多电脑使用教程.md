# GitHub 多电脑使用教程

GitHub 保存代码的中央版本；每台电脑保存自己的 API、图片和聊天记录。上传代码不会把另一台电脑的个人数据替换掉。

你的仓库：https://github.com/LuoJia00/cs1.1 。后续使用这个仓库，不需要再建立一个新的仓库。

## 一、让这台电脑显示在 GitHub Desktop 中

1. 从 https://desktop.github.com/ 安装 GitHub Desktop，登录 `LuoJia00` 账号。
2. 菜单 File → Add local repository，选择当前项目的文件夹。这个文件夹已初始化 Git，并连接到 `LuoJia00/cs1.1`。
3. 添加后，检查 Current repository 是 `cs1.1` 或当前项目文件夹名称，Current branch 是 `main`。
4. 首次上传由协助者完成；后续只需按下面的拉取和推送步骤操作。不需要重新创建仓库、重复初始化或重新复制整包。

GitHub 网页只用于查看代码；日常更新用 Desktop。原 LICENSE 要求二次开发保持开源且注明作者，发布时保留 LICENSE 和 README 中的来源说明。

## 二、另一台 Windows 电脑第一次使用

1. 安装 GitHub Desktop 并登录自己的同一个账号。
2. File → Clone repository → 选择你的仓库，存到 `D:\Infinite-Canvas` 等自己的目录。
3. 双击 `启动服务.bat`。第一次会自动下载项目专用的便携 Python、安装依赖并启动，需要能访问 python.org 和 pypi.org。
4. 等浏览器自动打开 http://127.0.0.1:3000/ 。以后启动仍然只需双击 `启动服务.bat`。
5. 如果自动安装失败，可单独双击 `安装依赖.bat` 查看完整错误后重试。
6. 在 API 页面填写配置。需要即梦等功能时，再安装并登录相应 CLI；浏览器插件也要在新电脑安装。

## 三、每次开始改代码前

1. 关闭画布服务窗口，避免程序正在运行时替换文件。
2. 在 GitHub Desktop 选中正确的仓库，点击 Fetch origin（检查云端）。
3. 出现 Pull origin 时，点击它下载更新。没有这个按钮且界面没有待拉取提示，说明已经同步。
4. 如果依赖清单变了，重新运行 `安装依赖.bat`。
5. 启动服务，开始使用或修改。

## 四、改完代码后

1. GitHub Desktop 的 Changes 会列出修改过的文件。
2. 检查文件和修改内容，只选这次要上传的代码。
3. Summary 写一句话，例如“修复图片导入”“调整工具栏布局”。
4. 点击 Commit to main：只保存到本机的版本记录。
5. 点击 Push origin：这一步才上传到 GitHub。
6. 到另一台电脑按第三节操作，即可获得相同的代码功能。

最容易记的顺序：开工先拉取，完工先提交、再推送。

## 五、两台电脑都改了代码怎么办

若本机还有未提交修改，先 Commit。推送被拒绝或提示远端有更新时，Fetch / Pull 后再 Push。

若提示冲突，表示同一部分代码有两种改法。保留好两边的提交，在 Desktop 中查看并解决冲突后再提交；不懂时把错误文字交给协助者。不要点 Discard changes，不要使用 force push，也不要用旧文件整包覆盖新代码。

## 六、可选：把 API 和提示词配置带到另一台电脑

1. 两边都先关闭画布服务。
2. 原电脑双击 `迁移配置.bat` → 输入 1 → 得到 `.private-transfer/settings-日期.zip`。
3. 通过自己的 U 盘等私下传到另一台电脑。它可能含 API 密钥且没有加密，不要上传 GitHub、群聊或公开网盘链接。
4. 新电脑双击 `迁移配置.bat` → 输入 2 → 拖入 zip → 回车 → 输入 YES。
5. 工具会先备份新电脑现有配置，再导入；重新启动服务。

此工具只迁移 API 服务商、全局配置、提示词库和 RunningHub 工作流配置。不会迁移图片、视频、画布、聊天记录、浏览器设置和账号登录。电脑目录路径需重新设置，外部 CLI 需重新登录；浏览器主题、部分选项需手动设置。

代码的 Push / Pull 不会自动同步个人配置。如仅更新功能，不需要重复迁移配置。

## 七、哪些文件不会上传

`API/.env`、`data/`、`assets/`、`output/`、`history.json`、`global_config.json`、`logs/`、`python/`、`.venv/`、`.local-backups/`、`.private-transfer/` 和运行时的 RunningHub 个人配置等均已排除。

程序使用的内置界面图片属于代码资源，会随项目保留；你的生成图片、素材和聊天附件不会上传。根目录新文件默认不上传，需要修改 `.gitignore` 白名单；不要为了上传而删除整个忽略文件。

原项目“在线更新”会下载原作者版本，现已在此维护版停用。今后统一使用 GitHub Desktop，更新后重新启动。

GitHub 官方操作说明：https://docs.github.com/en/desktop/adding-and-cloning-repositories
