# 公开信息研究工具包 rc.7 安装部署提示词

复制下方正文到目标电脑的 Codex。适用于首次安装或旧版升级；候选审查阶段不执行安装，固定 Release 与标签已公开后才执行。

---

请在这台电脑安装或升级 `public-info-research-kit`，固定版本为 **v0.8.0-rc.7**。

固定版本：https://github.com/xiem-public-info/public-info-research-kit/tree/v0.8.0-rc.7

发布与下载：https://github.com/xiem-public-info/public-info-research-kit/releases/tag/v0.8.0-rc.7

先确认上述 Release、标签和同版 ZIP 已公开；若仍未发布，保留现有版本并如实回报。阅读固定版本的 `RC_INSTALL_0.8.0.md`、`UPGRADE_0.8.0-rc.6_to_rc.7.md` 和 `RELEASE_NOTES_0.8.0-rc.7.md`。先核对已安装版本、市场来源与引用及实际安装目录；市场中的可用版本不能替代已安装版本。若实际已是 rc.7 且本版检查可调用，直接回报。

保留用户配置、项目文件、历史任务、证据和成果；不修改住宅公开 rc.8，不改其他市场或插件。优先使用当前 Codex 提供的 Plugin 安装或更新入口。需要 CLI 时先核本机帮助；首次登记本市场可以运行：

```bash
codex plugin marketplace add https://github.com/xiem-public-info/public-info-research-kit.git --ref v0.8.0-rc.7 --json
codex plugin add public-info-research-kit@public-info-research-public --json
```

已有市场固定 rc.6 或更早标签时，按升级说明处理这一市场。市场刷新只更新当前登记引用，不能证明跨标签更新或替换了旧插件缓存。重复 add 返回 alreadyAdded 也不能证明引用已改变。若需移除后重加，先明确本插件实际目录与配置，保护其中的用户自定义文件和成果，只操作本市场和本插件；不手动清空缓存或整个 Codex 配置。

更新后核对安装结果的 `version` 与 `installedPath`，读取该目录的 `.codex-plugin/plugin.json`，确认版本为 `0.8.0-rc.7`。在实际安装目录确认编译器提供 `--check-execution`，运行 `tests/run_execution_request_binding.py` 与 `tests/run_request_contract_binding.py` 两组共 64 项定点检查，并比对关键文件哈希；18 组完整发行回归仅在完整 ZIP 或仓库根目录运行，避免扫描其他插件缓存。新任务中确认七项能力可见。若只有市场快照是新版而已安装目录仍是旧版，回报未完成升级。

本版要求原生或住宅任务保留冻结原请求，实际执行前检查本次执行请求，研究充分性回传包含实际执行请求；后续授权另存绑定记录，不改原请求或住宅 rc.8 的采用回执。旧包仅显式只读审阅，缺实际回执不得伪造执行、自动补检索或直接升级为新版采用。原生任务沿用自己的业务 Owner；旧任务恢复仍遵从原停止要求。

完整 ZIP 的清单校验在完整解压目录运行。实际插件目录可能只含插件子目录，父级缺根清单时不能把 doctor 的 manifest_missing 当作安装失败而反复卸载；按升级说明分别核对完整包与实际加载代码。

Computer Use 的安装启用、系统权限和账号登录由我自行完成；不迁移 Cookie、token 或浏览器 profile。安装不启动微信、小红书、真实楼盘研究，也不自动恢复旧任务。若更新失败，保留已有成果，按升级说明恢复固定 rc.6，并明确回报回退后的实际版本。

最后简要回报实际安装版本和来源、离线检查、七项能力可见情况及需要我处理的环境条件。文件级升级回退测试不代表 Codex 插件缓存更新已在这台电脑验证；实际安装与真实渠道验收分别报告。
