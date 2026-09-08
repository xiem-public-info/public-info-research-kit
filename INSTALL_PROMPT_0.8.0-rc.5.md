# 公开信息研究工具包 rc.5 安装部署提示词

将下面正文复制到目标电脑的 Codex。适用于首次安装或从旧版升级；只使用公开仓库，不需要私有研发仓权限。

---

请在这台电脑安装或升级公开信息研究工具包 `public-info-research-kit`，固定版本为 **v0.8.0-rc.5**。

仓库：https://github.com/xiem-public-info/public-info-research-kit

固定版本：https://github.com/xiem-public-info/public-info-research-kit/tree/v0.8.0-rc.5

发布与下载：https://github.com/xiem-public-info/public-info-research-kit/releases/tag/v0.8.0-rc.5

先阅读这个固定版本的 `README.md`、`RC_INSTALL_0.8.0.md`、`QUICKSTART.md` 和 `RELEASE_NOTES_0.8.0-rc.5.md`，检查本机已安装版本与市场来源，再按当前 Codex 支持的方式安装。已有安装时保留用户配置、任务成果和账号状态；已是 rc.5 且能力可见时直接回报，不重复安装。

优先使用 Codex 的 Plugin 安装或更新入口。需要命令行时，先核对本机帮助；首次登记该市场的命令为：

```bash
codex plugin marketplace add https://github.com/xiem-public-info/public-info-research-kit.git --ref v0.8.0-rc.5
codex plugin add public-info-research-kit@public-info-research-public
```

若已有市场固定在旧标签，先按当前插件管理方式把这个市场的来源引用调整为 `v0.8.0-rc.5`，再更新本插件；不能把刷新旧标签当成升级成功，也不要改动其他市场或插件。

请落实本次更新：

1. 模型结合完整原请求与上下文理解任务；代码检查已记录动作和计划是否一致。明确排除有效，通用“QA”“分类”不改变业务领域，取图动作不能吞掉同时要求的分析。
2. 复用和暂缓不产生新检索；未解释部分保留原句，由执行者判断，不自动增加资格审查、搜索或用户填表。首次计划、用户增补和实质变更时回看原请求，保留原研究标准。
3. 住宅竞品名单只确定研究对象；临近交付不能直接判为尾盘，需核目标产品库存及销售阶段。关键结论保留证据和缺口，“本轮增量结束”不等于原研究充分完成。
4. 保留微信直接视觉路线；小红书通过当前 Computer Use 原生 App 入口操作正常可见 Chrome，不转入 CDP、浏览器接管或退役路线。参数错误先查当前接口说明，如实报告实际执行结果。

安装后核实实际安装的插件版本为 `0.8.0-rc.5`，确认七项能力可见：公开任务路由、网页与官方来源、微信已知链接、微信公开研究、小红书可见研究、地图空间证据、公开证据交付。当前任务未刷新能力时，提示我新建任务；环境异常时再用默认离线、只读的 doctor。

Computer Use 的安装启用、系统权限和账号登录由我自行完成；不代办、不迁移 Cookie、token 或浏览器 profile。安装流程不主动发起微信、小红书或全渠道检索；所需渠道在下一项已授权的正常业务中验证。

最后简要回报实际安装版本、来源、可见能力和仍需我处理的环境条件。该版本是预发布版，离线检查不证明模型理解、异机真实渠道或整晚运行已经稳定。
