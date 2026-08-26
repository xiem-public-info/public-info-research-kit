# 公开信息研究工具包 0.6.0

这是一个通过公开 GitHub 仓库分发的 Codex Plugin。个人和同事无需加入私有研发仓库，即可直接下载、安装与更新；它不是商业服务，也不对外承诺公众支持。

安装后即可使用七个 Skill：

- `public-info-intake-router`
- `public-web-official-resolver`
- `wechat-known-url-reader`
- `wechat-public-research`
- `xhs-visible-research`
- `map-spatial-evidence`
- `public-evidence-delivery`

## 安装

在 Codex 中打开本仓库，然后点击 Plugin 安装按钮；如果没有出现安装卡片，直接对 Codex 说：

> 安装这个 GitHub 仓库里的 public-info-research-kit Plugin。

Codex 会完成仓库注册和 Plugin 安装。当前任务未立即显示新 Skill 时，新建一个任务即可；只有 Plugin 仍不可见时才需要按 `TROUBLESHOOTING.md` 排查。

一条备用命令、更新和卸载方式见 `QUICKSTART.md`。`doctor` 只在安装或环境异常时使用，不是首次运行前置。

## 使用方式

安装后直接描述研究任务，不需要额外交接提示词或逐任务运行附件。

0.6.0 保留 D-235 研究型搜索策略，并把微信默认执行路线升级为 `WECHAT-LITE-DIRECT-CU-V1`：真人首次登录并打开公开“搜一搜”后，Codex 通过 Computer Use 直接完成一次查询输入、一次提交、开文、逐次正文推进和安全关页。该路线已在私有研发基线累计完成 25 条真实查询级链路验证，其中包括删除旧 V2 执行体系后的 5 条连续复验。

小红书继续使用本人既有、正常且可见的 Chrome；公开网页、官方文档和 OpenStreetMap 空间证据能力保持现行路线。聚合页和 AI 摘要只能用于发现线索，关键结论仍需回到可见原文。

微信与小红书使用自己的正常账号和本机正常界面，保持合理频率，不绕过登录、验证码、付费墙、权限墙或风控；账号和平台后果由使用者自行承担。微信真实检索前，请本人登录微信并手动打开公开“搜一搜”页面；中途除真实退出登录外，不要求真人重新打开。小红书由本人保持正常 Chrome 登录会话。同一台 Mac 上会争用鼠标、键盘或窗口焦点的任务应串行运行。

不迁移 Cookie、token、profile、扫码凭证或本地存储；不读取或保存私聊、通讯录和无关非公开信息。OSM 图件必须保留可见 `© OpenStreetMap contributors` 署名。

隐私、安全、排错与支持范围见 `PRIVACY.md`、`SECURITY.md`、`TROUBLESHOOTING.md` 和 `SUPPORT.md`。
