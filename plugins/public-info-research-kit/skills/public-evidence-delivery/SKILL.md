---
name: public-evidence-delivery
description: 将公开信息整理为可复盘证据包，区分事实候选、软证据、平台观察、冲突和缺口，并保留使用边界。
---

# 公开证据交付

1. 请求至少包含任务编号、对象、业务问题、所需证据、渠道／时间／地区范围、使用边界和停止条件。
2. 每条返回保留稳定指针、来源角色、原始声明、身份与时效、状态和必要限制。
3. 使用五类对象：`fact_candidate`、`soft_evidence`、`platform_observation`、`conflict`、`gap`。
4. 社交媒体观察和非概率样本不得自动升级为事实或总体比例；冲突不得静默覆盖；缺口必须写明原因和可重试条件。
5. 运行 `tools/package_evidence.py` 生成包，再用 `tools/validate_public_evidence.py` 做结构与敏感字段检查。
6. 不写入 Cookie、Token、请求头、浏览器状态、二维码凭证、本地存储、剪贴板内容或账号资料。
7. 微信／小红书证据必须回指 `query_id + exact_query_text`、查询计划版本、`searcher_mode`、来源角色和实际阅读覆盖；聚合线索只有回到真实原文后才能升级为证据。
8. 来源角色使用 `official_fact_source`、`brand_claim`、`sales_expression`、`supply_side_mechanism`、`buyer_voice`、`owner_experience`、`media_narrative`、`professional_workflow` 或 `ai_aggregate_clue`，避免创作者方法和销售叙事冒充用户声音。
9. 失败按 `query_semantic_failure`、`identity_collision`、`content_supply_gap`、`query_transport_failure`、`route_control_failure`、`source_render_failure`、`safety_stop`、`operator_transient_error_recovered` 和 `evidence_conversion_failure` 分层；只有前两类可直接反馈查询设计。

本 Skill 负责证据外壳，不替业务 Owner 作最终客户判断，也不向外部系统自动发送。

## 使用边界（0.5.0）

- 使用本人的正常账号和本机正常界面，保持合理频率；完整保留当前可见桌面研究能力。
- 不迁移、上传或交接 Cookie、token、profile、扫码凭证、本地存储、私聊、通讯录或非公开资料。
- 不绕过登录、验证码、付费墙、权限墙、风控或访问控制；出现安全确认时交由本人处理后继续。
- 依赖鼠标、键盘、窗口焦点或剪贴板的任务在同一台 Mac 上串行执行；这只是桌面冲突控制，不是授权机制。
- 引用第三方文字、图片、音视频或地图时保留必要来源与署名；OSM 图件保留可见 `© OpenStreetMap contributors`。
