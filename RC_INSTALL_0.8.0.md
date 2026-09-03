# v0.8.0-rc.2 中文安装与使用说明

这是供同事跨电脑试装的公开预发布版，不是稳定版。固定标签为 `v0.8.0-rc.2`，候选分支为 `codex/public-v0.8-quality-parity`；公开 `main / v0.7.0` 不受影响。

## 安装地址

- 候选分支：<https://github.com/xiem-public-info/public-info-research-kit/tree/codex/public-v0.8-quality-parity>
- 固定版本下载：[v0.8.0-rc.2](https://github.com/xiem-public-info/public-info-research-kit/releases/tag/v0.8.0-rc.2)

## 推荐安装方式

在 Codex 中发送候选分支地址，并说明：“请安装这个 GitHub 候选分支中的 `public-info-research-kit` Plugin。”

如果应用内安装没有成功，在终端依次执行：

```bash
codex plugin marketplace add https://github.com/xiem-public-info/public-info-research-kit.git --ref v0.8.0-rc.2
codex plugin add public-info-research-kit@public-info-research-public
```

安装完成后新建一个 Codex 任务，确认以下七个能力可见：公开任务路由、普通网页／官方来源、微信已知链接、微信公开研究、小红书可见研究、地图空间证据、公开证据交付。

## 第一次使用

普通公开网页、官方文档、Feed、离线校验和 OSM 后台任务可直接使用。例如：

> 请读取这个公开网页，整理关键事实、来源指针、冲突和缺口；不要把搜索摘要当作原文。

微信或小红书还需要终端用户自己完成以下准备：

1. 在 Codex Plugins 中自行安装并启用 Computer Use；本包不会代装或代启用。
2. 在 macOS 自行授予屏幕录制与辅助功能权限；本包不会读取或修改权限。
3. 登录自己的微信和小红书。微信首次手动打开公开“搜一搜”；小红书使用自己的正常、可见 Chrome 会话。
4. 登录、验证码、风控或页面不明时由本人处理；不得迁移 Cookie、token、profile 或扫码凭证。

## 每台电脑最小验收

- 先确认 Plugin 已安装且七个能力可见。
- 可选运行只读 doctor；它默认不联网，也不会安装 Computer Use、修改权限或操作登录。
- 普通网页至少完成一次“打开原页—读取事实候选—保留来源指针”。
- 需要微信时，完成一次低风险精确查询、打开一篇公开文章、正文推进至少两次并安全关页。
- 需要小红书时，完成一次低风险精确查询、打开一条公开笔记并读取实际可见正文、字幕、画面文字或评论。
- 微信／小红书只读，不点赞、不收藏、不评论、不关注、不发布；出现验证码、风控、异常自动化提示或画面歧义时停止。

完整检查清单见 [`INSTALL_CHECKLIST.md`](INSTALL_CHECKLIST.md)，逐机验收口径见 [`SMOKE_TESTS.md`](SMOKE_TESTS.md)。安装可见、doctor、真实渠道 smoke 和业务接受是不同状态，不能互相替代。

## 候选版边界

这个版本已经通过离线回归、发行文件完整性和干净克隆检查，但异机真实微信／小红书 smoke 与第二用户 UAT 仍需每位试装同事在自己的电脑和账号上完成。发现问题时请同时提供候选提交号、使用渠道、可复现步骤和停止位置；不要提交账号态、查询隐私、客户数据或截图中的敏感信息。
