---
name: xhs-visible-research
description: 在用户既有、正常且可见的 Chrome 中，通过桌面视觉操作执行低频小红书研究并生成脱敏证据。
---

# 小红书可见研究


收到用户或下游的检索合同，即默认授权全部检索渠道和公开搜索表面按需使用。下游只给业务目标、主体和内容需求；本工具包选择渠道、AI 使用顺序和精确词。AI→原文、原文→AI→后续计划均属常规研究。每条查询提交前冻结，范围内迭代无需另批；超出对象、目标或预算才请求裁定。权限不代表工具、登录、访问或真实渠道已验证。 规则见 `resources/retrieval_authority_current.json`，合同编译见 `tools/compile_retrieval_execution_request.py`。

## 唯一运行表面

只使用用户当前既有、正常、可见的 Chrome 与 Computer Use。不得使用浏览器调试接口、页面脚本、定位器、直接跳转、隔离或复制浏览器资料目录，也不得启用任何自动互动或发布。

当前入口为 `cua.getApp("com.google.Chrome")`，绑定原生 App；不得改用 `cua.getTab`、`cua.getBrowser`、`cua.createBrowserTab`。恢复或 API 报错后读取当前原生接口文档，核对签名；参数错误不能归为平台不可用或成为切换表面的理由。浏览器调试提示出现后停止并记录此前实际调用；不自动要求用户恢复窗口。已有有限重试授权继续有效，只有确需用户动作解除的阻塞才请协助。预检只证明合同匹配，不能证明真实调用合规。冻结前先核正式名与已证实别名。

终端用户自行安装并授权 Computer Use。公开包只提醒和检测，不安装、不启用、不授予系统权限，也不代替用户登录。

## 执行规则

1. 读取 `resources/channel-capability-profiles/xhs.v1.json`，先确认该渠道适配当前业务问题；不适配时返回其他渠道建议或缺口。
2. 使用本人的正常账号和本机正常界面，并确认没有其他任务占用共享可见桌面；不需要维护者签发运行附件。
3. 业务研究默认 `searcher_mode=researcher`。读取 `resources/social_semantic_query_lexicon.v0.1.json`，先闭合对象身份，再使用已经通过 `tools/validate_social_query_plan.py` 的冻结查询。
4. 真实 GUI 动作前生成 `portable_channel_request.v1` 并通过 `tools/check_portable_channel_preflight.py --require-live`。执行 Owner 是当前安装的公开信息研究包，业务问题、验收和解释仍归使用者或下游工程。
5. 搜索框出现旧词或错词时不提交；只允许在同一个正常 Chrome 中做一次受控替换。
6. 精确词逐字可见一致后才提交；失败时先诊断，并由真人决定是否进行一次有限重试，不自动启用垫板或其他路线。仍失败则记 `query_transport_failure`，不评价关键词效果。
7. 结果列表就绪后不得只看标题连续换词。达到任务阅读目标、充分推进两个结果批次仍无高质量候选、出现明显身份／主题漂移或触发停止线后，才可换到下一条冻结查询。
8. 验证码、登录、安全提示、风控、自动化提示或页面状态不明时立即停止并交给用户，记录 `safety_stop` 或 `route_control_failure`。
9. 只收集任务范围内可见内容；非概率样本只能作为关注信号或客户语言，不推断市场比例。
10. 视频笔记只报告实际可见标题、正文、字幕和画面文字；未播放或未听取的音频不得写成已覆盖。明确没有可见评论时记 `zero_visible_comments`。
11. 点点等聚合表面只用于扩词和回源线索；候选必须回到真实笔记、可见正文或评论后才进入证据。无法回源时记 `evidence_conversion_failure`。
12. 每条查询闭合时记录结果批次、实际开读数、来源角色覆盖、边际信息增益与失败归因。范围内增量按原任务授权逐条冻结后执行，超范围再请用户裁定。
13. 落盘前运行 `python tools/validate_xhs_evidence_security.py`，清除瞬态 URL 参数、账号态字段、请求头、浏览器资料路径和本地存储内容。

输出必须区分平台观察、软证据、冲突和缺口，不把小红书内容升级为项目硬事实。来源角色至少区分真实使用者声音、品牌／销售表达、媒体叙事、供给侧方法和聚合线索。

## 实际执行前的原请求检查

保留收到的原生或住宅请求原件。使用 `tools/compile_retrieval_execution_request.py --task <冻结原请求> --check-execution <本次执行请求>` 检查后，再执行其中的实际动作；编译成功或旧 live-gate 不能代替该检查。微信和小红书还需各自的 `--require-live` 预检。简单读取继续按原任务的直接读取适用性执行，不增加研究要求。研究回传保留本次实际 `execution_request`，不得事后重建成已执行；完整用法见 `skills/public-info-intake-router/SKILL.md`。

## 使用边界（0.8.0-rc.4）

- 使用本人的正常账号和本机正常界面，保持合理频率；完整保留当前可见桌面研究能力。
- 不迁移、上传或交接 Cookie、token、profile、扫码凭证、本地存储、私聊、通讯录或非公开资料。
- 不绕过登录、验证码、付费墙、权限墙、风控或访问控制；出现安全确认时交由本人处理后继续。
- 依赖鼠标、键盘、窗口焦点或剪贴板的任务在同一台 Mac 上串行执行；这只是桌面冲突控制，不是授权机制。
- 引用第三方文字、图片、音视频或地图时保留必要来源与署名；OSM 图件保留可见 `© OpenStreetMap contributors`。
