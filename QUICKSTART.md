# Quickstart

## 0.8.0-rc.7 预发布版

固定 rc.7 Release、标签与资产公开后才能安装；尚未公开时保持原版本。首次安装见 [中文安装说明](RC_INSTALL_0.8.0.md)，旧版升级见 [升级与回退步骤](UPGRADE_0.8.0-rc.6_to_rc.7.md)。可直接复制 [安装提示词](INSTALL_PROMPT_0.8.0-rc.7.md)。

当前 Plugin 页面提供安装入口时优先使用。核实实际 installedPath、版本和代码后，新建任务确认七项能力可见。安装不会启动真实检索，也不自动恢复旧任务。

## 开始任务

直接描述业务问题、使用范围和停止条件，例如：“请从这个官方公开网页提取发布日期、主体和关键事实，并把不确定项标为 gap。”无需额外交接提示词。

微信和小红书任务使用自己的正常账号、本机正常界面和合理频率。登录、验证码、安全确认或平台提示需要本人处理；工具不会迁移账号态，也不会绕过限制。安装后按 `SMOKE_TESTS.md` 对每台电脑、每个需要的渠道做一次最小真实 smoke。

## 按需依赖

普通使用不要求 Node/npm、Playwright 或 Chromium。只有处理 PDF 文档时，才按需安装 Python 依赖：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r plugins/public-info-research-kit/requirements/python-docs.txt
```

支持 CPython 3.12、3.13、3.14。环境或 Plugin 可见性异常时再运行：

```bash
python3 plugins/public-info-research-kit/tools/doctor.py --channel all
```

doctor 默认不联网，只读取本地版本、Plugin 清单和完整包布局中的文件完整性。实际插件目录可能只含子目录；父级缺根清单时按升级说明核对已校验 ZIP 与实际安装代码，不因此反复卸载。它可以判断 Computer Use 是否已安装启用，但不会安装、启用、读取 macOS 权限数据库、修改权限或操作账号登录。只有排查 TLS 时才显式增加 `--network-probe`。

## 更新和卸载

升级时保留原配置与成果，区分市场刷新、实际插件更新和新任务加载。固定旧标签的市场不会因刷新自动跨到新版，详见 [升级与回退](UPGRADE_0.8.0-rc.6_to_rc.7.md)。不手动清空缓存，不改其他市场或插件。

确需卸载时，先保护本插件目录中的用户自定义文件与成果，再使用 Plugin 页面或本机帮助确认的单插件 remove 命令。移除会删除其本地配置和缓存；项目目录里的历史成果继续保留。
