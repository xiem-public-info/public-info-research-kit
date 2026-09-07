---
name: public-evidence-delivery
description: 将公开信息整理为可复盘证据包，区分事实候选、软证据、平台观察、冲突和缺口，并保留使用边界。
---

# 公开证据交付

1. 已要求机器证据包时，由本包将原业务请求整理为任务编号、`request_id`、可空但不可省略的 `project_id`、对象、业务问题、所需证据、渠道／时间／地区范围、使用边界和停止条件。
2. 真实研究检索先按 `adaptive_query_sufficiency_contract.v1` 验证请求方的质量、数量、多样性、允许用途和停止条件；运行 `tools/validate_adaptive_query_sufficiency.py`，固定查询数不能替代充分性。
3. 每条返回保留稳定指针、来源角色、原始声明、身份与时效、状态和必要限制。
4. 使用五类对象：`fact_candidate`、`soft_evidence`、`platform_observation`、`conflict`、`gap`。
5. 社交媒体观察和非概率样本不得自动升级为事实或总体比例；冲突不得静默覆盖；缺口必须写明原因和可重试条件。
6. 上游状态只使用 `fulfilled`、`partial`、`gap`、`stopped`；`downstream_acceptance` 在上游包中必须保持 `not_assessed` 且 `decided_by=null`。没有冲突或缺口时仍分别输出空数组 `[]`。
7. 运行 `tools/package_evidence.py` 生成包，再用 `tools/validate_public_evidence.py` 做结构、消费者拒收与敏感字段检查。打包器不得改变证据类别、`negative_hits`、`conflicts`、`gaps` 或 `stop_reason`。
8. 不写入 Cookie、Token、请求头、浏览器状态、二维码凭证、本地存储、剪贴板内容或账号资料。
9. 微信／小红书证据必须回指 `query_id + exact_query_text`、查询计划版本、`searcher_mode`、来源角色、结果批次与实际开读数；标题浏览不计实际开读，聚合线索只有回到真实原文后才能升级为证据。
10. 来源角色使用 `official_fact_source`、`brand_claim`、`sales_expression`、`supply_side_mechanism`、`buyer_voice`、`owner_experience`、`media_narrative`、`professional_workflow` 或 `ai_aggregate_clue`，避免创作者方法和销售叙事冒充用户声音。
11. 失败按 `query_semantic_failure`、`identity_collision`、`content_supply_gap`、`query_transport_failure`、`route_control_failure`、`source_render_failure`、`safety_stop`、`operator_transient_error_recovered` 和 `evidence_conversion_failure` 分层；查询未正确提交不得记成语义失败，`content_supply_gap` 不得外推为全网没有。
12. 对异常动作、增量授权、查询晋升、软证据拒收和跨工程接受边界，按随 Plugin 安装的 `resources/decision-playbook.v1.md` 处理。

充分性按本任务可用的累计成果判断，包括可复用旧证据与新增证据，同一证据 ID 只计一次，不以单批新增计数代替累计计数。声明 `sufficient` 时，在现有充分性包中用 `receipt.cumulative_evidence` 引用已按本任务资格计入的证据；仅在原合同要求时附项目、来源或关键对象标识。`count_threshold` 和 `diversity_requirements` 表示原任务最低要求，`count_target` 和 `diversity_targets` 表示期望目标；由本工程据原意映射，不让下游另填技术表。质量及其他业务条件由 `requirement_assessments` 保留是否满足与证据依据，不新增评分。检查器拒绝与原要求矛盾的完成声明，但有效部分可按 `partially_sufficient` 交付；`remaining_gap` 中出现“缺”字不构成阻断，非关键缺口不否定已成立结果。

增益只记录任务适用且实际观察的维度，未测或不适用可省略，不能伪填零。保留总体判断与依据；只有原任务在 `marginal_gain_fields` 中已明确要求的维度才必填。A／B／C、项目多样性和表达类型均不作为所有研究的统一字段。

轻量阅读、素材和内部判断按用途直接交付，不为套用本 Skill 额外建包、建档或补齐无关字段。独立成立的结果可以先交付，原任务是否完成仍按业务目标判断。图片先看对象、视角、用途缺口，再选最可能补齐的来源；已有截图满足研究用途时先用，入选正式图片需要清晰度时再定向补取原图。完整购房事件沿用下游已裁定定义，按需记录希望取得的进展（desired_progress），区分原声、推断和未取得；不新增统一因素、不回填历史或因此扩搜。

本 Skill 负责证据外壳，不替业务 Owner 作最终客户判断，也不向外部系统自动发送。


收到用户或下游的检索合同，即默认授权全部检索渠道和公开搜索表面按需使用。下游只给业务目标、主体和内容需求；本工具包选择渠道、AI 使用顺序和精确词。AI→原文、原文→AI→后续计划均属常规研究。每条查询提交前冻结，范围内迭代无需另批；超出对象、目标或预算才请求裁定。权限不代表工具、登录、访问或真实渠道已验证。 规则见 `resources/retrieval_authority_current.json`，合同编译见 `tools/compile_retrieval_execution_request.py`。

## 使用边界（0.8.0-rc.3）

- 使用本人的正常账号和本机正常界面，保持合理频率；完整保留当前可见桌面研究能力。
- 不迁移、上传或交接 Cookie、token、profile、扫码凭证、本地存储、私聊、通讯录或非公开资料。
- 不绕过登录、验证码、付费墙、权限墙、风控或访问控制；出现安全确认时交由本人处理后继续。
- 依赖鼠标、键盘、窗口焦点或剪贴板的任务在同一台 Mac 上串行执行；这只是桌面冲突控制，不是授权机制。
- 引用第三方文字、图片、音视频或地图时保留必要来源与署名；OSM 图件保留可见 `© OpenStreetMap contributors`。
