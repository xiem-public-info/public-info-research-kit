# Quickstart

## 一步安装

在 Codex 中打开本仓库并安装 Plugin。若没有出现安装卡片，直接让 Codex“安装这个 GitHub 仓库里的 `public-info-research-kit` Plugin”，无需手动执行底层命令。

安装成功后即可开始任务。当前任务没有刷新出新 Skill 时，新建任务；不要把重启或 doctor 当作正常安装步骤。

## 备用 CLI

只有应用内安装没有成功时，才复制执行这一条：

```bash
codex plugin marketplace add xiem-public-info/public-info-research-kit && codex plugin add public-info-research-kit@public-info-research-public
```

## 开始任务

直接描述业务问题、使用范围和停止条件，例如：“请从这个官方公开网页提取发布日期、主体和关键事实，并把不确定项标为 gap。”无需额外交接提示词。

微信和小红书任务使用自己的正常账号、本机正常界面和合理频率。登录、验证码、安全确认或平台提示需要本人处理；工具不会迁移账号态，也不会绕过限制。

## 按需依赖

普通使用不要求 Node/npm、Playwright 或 Chromium。只有处理 PDF 文档时，才按需安装 Python 依赖：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r plugins/public-info-research-kit/requirements/python-docs.txt
```

支持 CPython 3.12、3.13、3.14。环境或 Plugin 可见性异常时再运行：

```bash
python3 plugins/public-info-research-kit/tools/doctor.py
```

## 更新

优先在 Codex 的 Plugin 页面点击更新。备用命令：

```bash
codex plugin marketplace upgrade public-info-research-public && codex plugin add public-info-research-kit@public-info-research-public
```

从 0.4.0 更新到 0.5.0 不需要先卸载。更新完成后新建一个任务即可使用新规则；无需重启 Codex，也不要把 doctor 当作更新前置。微信任务开始前，本人需登录微信并手动打开“搜一搜”页面、保持在前台。

0.5.0 的更新验收见 `UPDATE_0.5.0.md`。

## 卸载

优先在 Codex 的 Plugin 页面点击卸载。备用命令：

```bash
codex plugin remove public-info-research-kit@public-info-research-public && codex plugin marketplace remove public-info-research-public
```
