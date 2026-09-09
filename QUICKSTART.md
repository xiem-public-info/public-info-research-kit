# Quickstart

## 0.8.0-rc.6 候选版

公开 main 已同步 0.8.0-rc.6；固定版本安装可使用 `v0.8.0-rc.6` 标签。中文地址、命令和逐机验收说明见 [`RC_INSTALL_0.8.0.md`](RC_INSTALL_0.8.0.md)。需要旧稳定版时使用 `v0.7.0` 标签。

## 一步安装

在 Codex 中打开本仓库并安装 Plugin。若没有出现安装卡片，直接让 Codex“安装这个 GitHub 仓库里的 `public-info-research-kit` Plugin”，无需手动执行底层命令。

安装成功后即可开始任务，无需联系维护者或取得逐任务授权。当前任务没有刷新出新 Skill 时，新建任务；不要把重启或 doctor 当作正常安装步骤。

需要微信或小红书时，终端用户另行在 Codex Plugins 中自行安装并启用 Computer Use，并自行授予 macOS 屏幕录制与辅助功能权限；本包不会代办。随后登录自己的微信和小红书。完整清单见 `INSTALL_CHECKLIST.md`。

## 备用 CLI

只有应用内安装没有成功时，才复制执行这一条：

```bash
codex plugin marketplace add https://github.com/xiem-public-info/public-info-research-kit.git --ref v0.8.0-rc.6 && codex plugin add public-info-research-kit@public-info-research-public
```

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

doctor 默认不联网，只读取本地版本、Plugin 清单和文件完整性。它可以判断 Computer Use 是否已安装启用，但不会安装、启用、读取 macOS 权限数据库、修改权限或操作账号登录。只有排查 TLS 时才显式增加 `--network-probe`。

## 更新

升级到本版可复制 [rc.6 安装部署提示词](INSTALL_PROMPT_0.8.0-rc.6.md)。若市场来源固定旧标签，先将其引用调整到 `v0.8.0-rc.6` 再更新；下方 upgrade 命令仅刷新当前登记的引用，不自动跨标签升级。

优先在 Codex 的 Plugin 页面点击更新。备用命令：

```bash
codex plugin marketplace upgrade public-info-research-public && codex plugin add public-info-research-kit@public-info-research-public
```

从 0.4.0—0.7.0 更新到 0.8.0 不需要先卸载。更新完成后新建一个任务即可使用新规则；无需重启 Codex，也不要把 doctor 当作更新前置。微信任务开始前，使用者需登录微信、手动打开公开“搜一搜”，并让该页面保持在 Computer Use 当前可操作的主屏执行面。

0.8.0 候选的更新范围与验收边界见 `UPDATE_0.8.0.md`。在正式标签发布前，普通用户继续以 0.7.0 为稳定版。

## 卸载

优先在 Codex 的 Plugin 页面点击卸载。备用命令：

```bash
codex plugin remove public-info-research-kit@public-info-research-public && codex plugin marketplace remove public-info-research-public
```
