# 终端安装检查清单

适用于每一台新电脑、每一个独立 Codex 用户。公开信息研究包不会迁移另一台电脑的账号、插件、权限或登录态。

1. 在 Codex 中安装并启用 `public-info-research-kit`，新建一个任务确认七个 Skill 可见。
2. 如果只使用普通公开网页、官方文档、Feed、离线校验或 OSM 后台处理，不要求 Computer Use。
3. 如果要使用微信或小红书，终端用户自行在 Codex Plugins 中安装并启用 Computer Use。本包只提醒和检测，不安装、不启用。
4. 终端用户自行在 macOS 授予 Computer Use 所需的屏幕录制与辅助功能权限。本包和 doctor 不读取系统权限数据库，也不修改权限。
5. 终端用户登录自己的微信和小红书：微信首次手动打开公开搜一搜；小红书保留自己的正常、可见 Chrome 会话。
6. 可选运行只读 doctor：`python3 tools/doctor.py --channel all`。默认不联网；只有排查 TLS 时才显式加 `--network-probe`。
7. 按 `resources/per-machine-smoke.v1.md` 完成所需渠道的最小真实 smoke。安装可见、doctor、真实渠道 smoke 和业务接受必须分别记录。

不要把 Cookie、token、扫码凭证、浏览器 profile、Local Storage、请求头、私聊、通讯录或客户数据放进 doctor 输出、smoke 回执、Issue 或交接包。
