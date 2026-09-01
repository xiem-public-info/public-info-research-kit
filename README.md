# 公开信息研究工具包 0.8.0-rc.1 候选

当前分支已公开供同事安装和 RC 验收，但尚未作为正式 Release 发布；公开 `main` 与正式标签在真人批准前仍保持 0.7.0。本页描述候选包的完整目标能力，不代表异机真实 smoke 或正式发行已经完成。候选版中文安装说明见 [`RC_INSTALL_0.8.0.md`](RC_INSTALL_0.8.0.md)。

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

如果要使用微信或小红书，终端用户还需要在 Codex Plugins 中自行安装并启用独立的 Computer Use、在 macOS 自行授予所需权限，并登录自己的微信和小红书。本发行包只提醒和检测，不代装、不代启用、不改权限、不代登录。普通公开网页、官方文档、Feed、离线校验和 OSM 后台能力不依赖 Computer Use。

完整步骤见 `INSTALL_CHECKLIST.md`；每台电脑的最小真实验收见 `SMOKE_TESTS.md`。一条备用命令、更新和卸载方式见 `QUICKSTART.md`。`doctor` 只在安装或环境异常时使用，默认完全离线、只读，不是首次运行前置。

## 使用方式

安装后直接描述研究任务，不需要额外交接提示词或逐任务运行附件。

0.8.0-rc.1 保留研究型搜索策略和微信 `WECHAT-LITE-DIRECT-CU-V1` Stable 路线：使用者首次登录并打开公开“搜一搜”后，Codex 通过 Computer Use 直接完成一次查询输入、一次提交、开文、逐次正文推进和安全关页。该路线已在研发基线完成跨批次真实链路验证；发行包不包含旧 V2、Pad 或 AX 路线。

候选发行范围包括：四类渠道能力画像、完整可移植 D-235 语义查询核心、D-237 充分性／自适应增量／查询晋升、微信搜一搜、小红书既有正常 Chrome、静态公开网页、无需账号的公开动态页、官方 HTML/PDF、必要页 OCR、RSS/公开 Feed、OpenStreetMap/POI、证据拒收和住宅 UE v0.2 互操作锁。RSS/Feed 只负责发现；聚合页和 AI 摘要只能用于线索，关键结论必须回到可见原文。

不属于本发行包的能力包括：机构数据库、土地数据库、明源周报运行服务、已退役的 MediaCrawler/CDP/XHS Searcher、微信 V2/Pad/AX，以及尚未形成现行能力的抖音、视频号和垂直小程序。

微信与小红书使用自己的正常账号和本机正常界面，保持合理频率，不绕过登录、验证码、付费墙、权限墙或风控；账号和平台后果由使用者自行承担。微信真实检索前，请使用者登录微信并手动打开公开“搜一搜”页面，并让搜一搜保持在 Computer Use 当前可操作的主屏执行面；中途除真实退出登录外，不要求重新打开。小红书由使用者保持正常 Chrome 登录会话。同一台 Mac 上会争用鼠标、键盘或窗口焦点的任务应串行运行。

不迁移 Cookie、token、profile、扫码凭证或本地存储；不读取或保存私聊、通讯录和无关非公开信息。OSM 图件必须保留可见 `© OpenStreetMap contributors` 署名。

本项目采用 MIT License，允许使用、修改、再分发和商业使用，但必须保留版权与许可证文本；软件按原样提供，不作担保。隐私、安全、排错与支持范围见 `PRIVACY.md`、`SECURITY.md`、`TROUBLESHOOTING.md` 和 `SUPPORT.md`。

渠道能力强弱项见 `CAPABILITY_MATRIX.md`；黄金决策经验见 `DECISION_PLAYBOOK.md`；跨工程接口见 `INTEROPERABILITY.md`。离线回归、安装可见、doctor、真实渠道 smoke 和业务接受是不同状态，不能互相替代。
