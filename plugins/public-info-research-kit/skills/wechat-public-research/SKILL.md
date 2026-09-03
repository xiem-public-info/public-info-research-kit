---
name: wechat-public-research
description: 在真人首次预开的微信公开搜一搜中，以 Direct Computer Use 完成精确查询、开文、正文推进和安全关页。
---

# 微信 Lite 公开文章研究

仅在任务已明确要求微信关键词检索或公众号账号清单研究时使用。`wechat_ai_search` 当前只提供离线 Gate，不进入本 Skill 的真实执行热路径。

## 前置条件

- 读取 `resources/channel-capability-profiles/wechat.v1.json`，先确认该渠道适配当前业务问题；不适配时返回其他渠道建议或缺口。
- 社媒查询计划已通过 `tools/validate_social_query_plan.py`，本次微信查询具有冻结的 `query_id + exact_query_text`。
- 已生成 `portable_channel_request.v1` 并通过 `tools/check_portable_channel_preflight.py --require-live`；执行 Owner 是当前安装的公开信息研究包，业务问题、验收和解释仍归使用者或下游工程。
- 使用本人的正常账号和本机正常界面。
- 当前没有其他任务占用共享可见桌面；不依赖维护者邀请、私有仓或签发运行附件。
- 微信登录态由使用者本人维护；不得导出、复制或写入发行包。
- 终端用户自行安装并授权 Computer Use。公开包只提醒和检测，不安装、不启用、不授予系统权限，也不代替用户登录。
- 当前可靠启动方式是使用者先登录微信并手动打开公开“搜一搜”，并让该页面保持在 Computer Use 当前可操作的主屏执行面。Plugin 从可见搜一搜页面开始；中途除微信真实退出登录外，不要求使用者重新打开。

## 微信 AI 搜索表面边界

- 若路由结果为 `aggregate_ai_gate_preparation`，读取 `resources/channel-capability-profiles/wechat-ai-search.v1.json`，并运行 `tools/check_wechat_ai_search_gate_preflight.py`。
- 当前状态上限是 `gate_ready_not_live_validated`：`execution_authorized=false`、`real_gui_validated=false`。不得打开微信 AI、输入真实查询、操作登录或借普通搜索冒充聚合表面。
- 聚合输出只能交付对象解歧、信息密度、标题、账号、日期、生命周期、冲突、反例和原始来源导航线索；正式消费前必须用新的独立查询回到普通微信文章表面和原文。
- 未来 live 能力需由具名真实任务另行冻结查询、频率、配额、停止线和验收口径，并取得用户明确授权；本候选不预授予。

## 关键词模式：`WECHAT-LITE-DIRECT-CU-V1`

1. 从最新完整画面确认公开搜一搜以及不存在登录、验证码、安全、频率或私域风险。
2. 根据当前画面新鲜定位并点击搜索框；不得复用固定坐标或缓存元素。
3. 按一次 `super+a` 选中旧词，通过 Computer Use `paste()` 直接粘贴 `exact_query_text` 一次。
4. 读取一次最新完整画面并逐字确认。即使工具返回 `-10005`，只要完整查询词已正确可见，即按业务成功继续；否则停止，不做第二次粘贴。
5. 按一次 `Return`，确认结果刷新。加载中只做有界等待和再次观察，不重复提交。
6. 动态打开一篇明确相关的公开文章，动作后确认文章身份。
7. 正文默认逐次按 `Next`，每次只读取一次动作后的最新完整画面。内容未推进时最多重新点击正文一次，再失败即停止本篇。
8. 达到 `full_to_bottom` 或合格的 `relevant_sections_only` 后，按一次 `super+w` 并确认返回结果页。
9. 整篇完成且安全关页后再综合研究卡片，不逐屏成稿。

正常路径不使用查询垫板、AX、DOM、Playwright、journal、checkpoint、proof、spool 或手工机器回执。

## 三态异常原则

- 可观察成功：继续。
- 可观察失败：只允许一次低风险纠正，或停止。
- 不可观察或有歧义：放弃当前查询，不重复粘贴、提交、开文或关页。

不为异常另建恢复状态机，也不自动切换旧路线。

## 账号清单模式

先用 `tools/validate_wechat_account_list.py` 校验账号身份、别名和查询策略，再用 `tools/build_wechat_account_query_plan.py` 生成确定性的精确查询清单。逐账号记录 `fulfilled`、`partial` 或 `gap`；所有输入账号都必须有终态，跨查询重复文章按稳定指针去重。

## 文章阅读

从搜索结果打开文章时，至少保留一批结果列表锚点和候选编号。首开只有标题但正文延迟时，先阅读另一篇可读文章再回访一次；仍不可读才记为 `source_render_failure`。

结果列表就绪后应用 `query_dwell_gate`：只有达到任务冻结的高质量开文／阅读目标、已浏览两个内容确有推进的结果批次仍无高质量候选、出现明显身份／主题漂移，或触发停止线时才能换词。不得只看首屏标题连续切换查询。宽到细任务必须先形成当前阶段结论再进入下一阶段。

每个查询结束时记录查询效果、结果批次、实际开文数、来源角色覆盖、边际信息增益和失败类别。只有正确提交且充分查看后的低相关结果才能记 `query_semantic_failure`；输入、窗口、渲染和安全停止不得拿来评价关键词质量。业务语义内核可以提出下一批查询，但未获 `adaptive_extension` 授权且未冻结为可执行查询前不得继续运行。

## 停止线

验证码、登录、安全提示、风控、焦点不明、账号身份含混、页面不可读或共享桌面冲突出现时立即停止并回报；不得尝试绕过。若出现 `noWindowsAvailable`，先把它视为搜一搜离开当前主屏可操作执行面的环境信号：停止当前歧义动作，不重复粘贴或提交；由使用者恢复主屏布局后在新任务或新操作上下文继续，不自动搬窗、重启微信或建设恢复状态机。分别使用 `query_transport_failure`、`route_control_failure`、`source_render_failure` 或 `safety_stop`，不要笼统写成搜索失败。

## 使用边界（0.8.0-rc.2）

- 使用本人的正常账号和本机正常界面，保持合理频率；完整保留当前可见桌面研究能力。
- 不迁移、上传或交接 Cookie、token、profile、扫码凭证、本地存储、私聊、通讯录或非公开资料。
- 不绕过登录、验证码、付费墙、权限墙、风控或访问控制；出现安全确认时交由本人处理后继续。
- 依赖鼠标、键盘、窗口焦点或剪贴板的任务在同一台 Mac 上串行执行；这只是桌面冲突控制，不是授权机制。
- 引用第三方文字、图片、音视频或地图时保留必要来源与署名；OSM 图件保留可见 `© OpenStreetMap contributors`。
