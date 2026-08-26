# 更新与验收 0.6.0

## 更新范围

0.6.0 将微信关键词研究从 0.5.0 的查询垫板路线切换为 `WECHAT-LITE-DIRECT-CU-V1`。小红书、公开网页、官方文档、OpenStreetMap 空间证据和证据交付能力继续保留。

## 更新方法

优先在 Codex Plugin 页面点击更新。备用命令见 `QUICKSTART.md`。从 0.4.0 或 0.5.0 更新时无需先卸载；更新完成后新建一个任务。

## 最小验收

1. Plugin 版本显示为 0.6.0，并包含七个 Skill。
2. 运行 `python3 plugins/public-info-research-kit/tools/doctor.py` 时，`skill_count` 与 `sensitive_files` 为 `pass`；未安装到当前环境时 `plugin_visibility` 可单独为 `gap`。
3. 微信任务由本人登录并首次打开公开“搜一搜”；Codex 应采用一次直接粘贴、一次提交、开文、逐次 `Next` 和一次 `super+w`，不得调用查询垫板。
4. 小红书仍使用本人既有、正常且可见的 Chrome，不使用调试接口、隔离 profile 或自动 fallback。
5. OSM 图件保留清晰可见的 `© OpenStreetMap contributors` 署名。

本验收只确认公开包安装和规则接线；真实渠道结果仍取决于使用者账号、当前页面和任务内容供给。
