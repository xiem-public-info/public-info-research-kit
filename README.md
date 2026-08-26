# 公开信息研究工具包 0.7.0

这是一个通过公开 GitHub 仓库分发的 Codex Plugin。任何符合环境条件的使用者都可以直接下载、安装与更新，无需加入私有研发仓库，也无需维护者或原作者逐任务授权。它不是托管采集服务；支持范围见 `SUPPORT.md`。

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

0.7.0 保留研究型搜索策略和微信 `WECHAT-LITE-DIRECT-CU-V1` Stable 路线：使用者首次登录并打开公开“搜一搜”后，Codex 通过 Computer Use 直接完成一次查询输入、一次提交、开文、逐次正文推进和安全关页。该路线已在研发基线完成跨批次真实链路验证；发行包不包含旧 V2、Pad 或 AX 路线。

现行发行范围包括：微信搜一搜、小红书既有正常 Chrome、静态公开网页、无需账号的公开动态页、官方 HTML/PDF、必要页 OCR、RSS/公开 Feed 发现、OpenStreetMap/POI 空间证据，以及查询设计、来源分层、充分性判断和证据交付。RSS/Feed 只负责发现，动态页和每个新来源仍需按当次页面核验；聚合页和 AI 摘要只能用于发现线索，关键结论必须回到可见原文。

不属于本发行包的能力包括：机构数据库、土地数据库、明源周报运行服务、已退役的 MediaCrawler/CDP/XHS Searcher、微信 V2/Pad/AX，以及尚未形成现行能力的抖音、视频号和垂直小程序。

微信与小红书使用自己的正常账号和本机正常界面，保持合理频率，不绕过登录、验证码、付费墙、权限墙或风控；账号和平台后果由使用者自行承担。微信真实检索前，请使用者登录微信并手动打开公开“搜一搜”页面，并让搜一搜保持在 Computer Use 当前可操作的主屏执行面；中途除真实退出登录外，不要求重新打开。小红书由使用者保持正常 Chrome 登录会话。同一台 Mac 上会争用鼠标、键盘或窗口焦点的任务应串行运行。

不迁移 Cookie、token、profile、扫码凭证或本地存储；不读取或保存私聊、通讯录和无关非公开信息。OSM 图件必须保留可见 `© OpenStreetMap contributors` 署名。

本项目采用 MIT License，允许使用、修改、再分发和商业使用，但必须保留版权与许可证文本；软件按原样提供，不作担保。隐私、安全、排错与支持范围见 `PRIVACY.md`、`SECURITY.md`、`TROUBLESHOOTING.md` 和 `SUPPORT.md`。
