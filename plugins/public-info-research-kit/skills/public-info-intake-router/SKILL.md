---
name: public-info-intake-router
description: 将研究问题路由到微信、小红书、静态或动态公开网页、官方文档、RSS/Feed、地图空间证据和证据交付能力；只生成计划，不直接执行平台动作。
---

# 公开信息研究入口

当用户提出跨渠道研究、渠道选择、检索计划或证据需求时使用本 Skill。


收到用户或下游的检索合同，即默认授权全部检索渠道和公开搜索表面按需使用。下游只给业务目标、主体和内容需求；本工具包选择渠道、AI 使用顺序和精确词。AI→原文、原文→AI→后续计划均属常规研究。每条查询提交前冻结，范围内迭代无需另批；超出对象、目标或预算才请求裁定。权限不代表工具、登录、访问或真实渠道已验证。 规则见 `resources/retrieval_authority_current.json`，合同编译见 `tools/compile_retrieval_execution_request.py`。

## 工作合同

1. 先确认业务问题、需要什么证据、使用边界和停止条件。
2. 下游只需提供 `task_id`、`business_question`、`subjects` 与已有业务限制；本包生成渠道计划，随后运行 `python tools/route_task.py --request <请求文件>`。
3. 读取路由结果中的 `capability_profile`。它说明该渠道擅长、不擅长、黄金方法、失败分类和停止线；不要用一个渠道的经验替代另一个渠道的画像。
4. 对真实研究检索先生成 `query_sufficiency_applicability.v1`，运行 `python tools/validate_adaptive_query_sufficiency.py --applicability-input <适用性文件>`。未显式声明时默认 `d237_required`；缺少 `acceptance_mode` 时返回 `d237_consumer_contract_required`，不得静默降级。只有具名链接读取、指定文件获取、单事实核验或精确记录读取，且有真人豁免引用时，才可用 `exempt_simple_direct_retrieval`。
5. 微信／小红书业务研究默认 `searcher_mode=researcher`。先闭合城市、正式名、单一别名、分期、主体和时间阶段；同名、异体字或历史名分别生成独立查询，不塞进一个长查询。
6. 读取 `resources/social_semantic_query_lexicon.v0.1.json`，围绕 `business_question + judgment_gap`，用身份、生命周期、业务意图、渠道表面、来源角色、体验机制、客户任务、比较角色、反例、内容形态和时间等语义原子形成少量查询候选。
7. 把查询写入 `social_query_plan.v1`。每条须有唯一 `query_id`、独立 `exact_query_text`、执行状态、查询假设、来源角色目标、结果批次下限、实际开读下限、预期信息增益和失败归因要求；运行 `python tools/validate_social_query_plan.py --plan <计划文件>`，只有 `executable_query_ids` 中的冻结查询可执行。
8. 住宅比较研究在深搜前完成身份、当前新房供给、近六个月内容、开盘／加推／实际可选产品、交付期和适用产品层的轻量生命周期核验；不足 12 个月到交付只建议下游降为尾盘参照，不替下游裁定正式竞品角色。
9. 研究任务的首次回传要主动检查项目事实、竞品关系、客户选择和反例是否共同支持统一语义核；完整事件分别统计项目归属与全局独立家庭旅程；官方表达同时保留核心观点、必要短原话和原文定位。用 `d292_research_orchestration.v1` 和 `tools/validate_d292_research_orchestration.py` 校验这些边界。
10. 业务语义内核可以依据负例、冲突、缺口和边际信息增益生成一份合并 `proposed_incremental`，范围内按原任务授权逐条冻结后执行，超范围另行裁定。形成或验收充分性包时运行 `python tools/validate_adaptive_query_sufficiency.py --input <充分性包>`。
11. 本包用 `tools/compile_retrieval_execution_request.py --task <收到的业务合同> --plan <本包计划> --output <执行请求>` 编译。计划含 `channel`、`surface_id` 和 `queries`；每条查询含编号、精确词、frozen 状态和任务配额。`shared_gui`、`computer_use`、`end_user_session` 由本包核实际环境后填写，不能要求下游填写或自动假定为已就绪。微信 AI 编译结果直接交 AI 预检；其他微信／小红书在真实 GUI 动作前，把冻结查询转换为 `portable_channel_request.v1`，运行 `python tools/check_portable_channel_preflight.py --request <请求文件> --require-live`。执行 Owner 固定为已安装的公开信息研究包；下游保留业务问题、验收和解释权，不能指定执行器、回退、坐标或登录态。
12. `wechat_ai_search` 与 `xhs_ask_diandian` 是两个独立平台表面，普通搜索不得冒充；聚合回答只用于解歧、信息密度、扩词、反例和回源导航。微信 AI 从任务合同继承权限，运行 `tools/check_wechat_ai_search_gate_preflight.py --require-live` 检查实际执行条件，结果不代表已执行或已通过真实验收。
13. 只采用路由器返回的发行能力，不搜索或调用仓库外的历史路线。
14. 微信、小红书使用本机正常账号和可见桌面；路由结果只是计划。执行时保持合理频率，并确保同一时刻只有一个任务操作共享可见桌面。
15. 普通网页、官方文档、RSS/Feed 和后台地图处理可并行；公开动态页先做静态探针，确需浏览器渲染时再进入受控运行态读取。若需要操作共享可见桌面，则与其他桌面任务串行，并始终遵守任务范围、访问权限与来源许可。
16. RSS/Feed 只作低频发现层：条目必须保留 feed URL、原站 URL、发布时间和去重键；摘要不能替代原文，关键结论必须回到原站 Resolver。
17. 只有当前检索任务自然闭合后才换任务线程；不要在进行中催促、插入下一批或把换线程当作平台恢复动作。
18. 遇到“动作报错但画面成功”“标题未开文”“两批无高质量候选”“聚合命中”“软证据拒收”等情形，按随 Plugin 安装的 `resources/decision-playbook.v1.md` 处理。
19. 若输入不足，只返回真正影响检索的问题；其他缺口按明确假设继续，不要求使用者填写复杂表格。

## 输出

输出必须包含：任务编号、业务问题、判断缺口、渠道与模式、渠道画像、业务 Owner、执行 Owner、`searcher_mode`、对象身份、精确输入、查询计划版本、每条查询的最小结果批次与实际开读数、增量授权状态、证据目标、使用边界、停止条件和预期验证器。

本 Skill 不打开微信、小红书、浏览器或地图，不联网，不生成平台事实，也不代表真实检索已经完成。

## 使用边界（0.8.0-rc.3）

- 使用本人的正常账号和本机正常界面，保持合理频率；完整保留当前可见桌面研究能力。
- 不迁移、上传或交接 Cookie、token、profile、扫码凭证、本地存储、私聊、通讯录或非公开资料。
- 不绕过登录、验证码、付费墙、权限墙、风控或访问控制；出现安全确认时交由本人处理后继续。
- 依赖鼠标、键盘、窗口焦点或剪贴板的任务在同一台 Mac 上串行执行；这只是桌面冲突控制，不是授权机制。
- 引用第三方文字、图片、音视频或地图时保留必要来源与署名；OSM 图件保留可见 `© OpenStreetMap contributors`。
