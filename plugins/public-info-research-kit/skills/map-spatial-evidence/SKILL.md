---
name: map-spatial-evidence
description: 将调用方给定的项目、配套和参照对象转为中心点、距离、阻隔与相对便利性证据；不裁定竞品，不负责绘图。
---

# 地图与空间证据

先读取 Plugin 根目录下的 `resources/channel-capability-profiles/osm-spatial.v1.json`。新任务采用 D-291 的 `spatial_coordinate_evidence.v2`，不再以图件显示验收作为前置。

1. 接收调用方已经确定的本案、竞品、配套与参照对象清单，不自行裁定竞品关系。
2. 本案、竞品及紧凑配套各取地图平台的一个标注中心点。不查实际入口、售楼部、多锚点、项目边界或最近边界。
3. 步行、驾车从中心点发起，接受平台自动吸附道路；区分直线、步行、驾车距离。公园、河流、道路等大型或狭长资源用中心点到资源几何的最短直线距离，称为“垂距”。
4. 尽量提供本案顺时针四角点、相邻道路／路口名称及坐标，供下游绘制近似轮廓；无法识别时注明不可用，不阻断已完成的中心点、距离和阻隔结果。角点不作为距离起点。
5. 记录实际可观察的主干道、河流、高差、围墙和未开放通道等阻隔，只在调用方给定集合内判断距离或步行便利性，不输出绝对“独占配套”。
6. 按 `tests/fixtures/spatial_coordinate_evidence_v2/schema.json` 组织数据，使用 `tools/validate_spatial_coordinate_evidence_v2.py` 校验。校验仅证明结构与业务边界，不证明真实地图坐标或路线正确。

按对象部分交付：可靠点位照常交付；未取得的对象用 `location_status=not_available` 与 `gap_reason` 保留，坐标不伪填。任务用途已经接受的门牌或区域示意用 `approximate_only`，保留 `accepted_use_ref` 和用途限制，不冒充精确中心点，也不用于精确距离或路线计算。检查器的 `delivery_status=partial` 不代表任务完成；本案或关键精度缺失时按原业务目标保留未完成。

普通交付只呈现坐标、距离、阻隔、相对便利性和必要缺口；地图平台、坐标制式、采集日期留在后台便于复算，不向客户正文堆放工程状态。

本渠道不绘图。旧 `tools/assemble_osm_asset.py` 和 `tools/validate_osm_display_receipt.py` 仅保留用于历史或独立下游显示任务，不是新空间任务必经步骤。实际使用 OSM 底图、截图或拼接资产时才要求可见 `© OpenStreetMap contributors` 署名；未使用 OSM 资产不强制署名。OSM Standard 不得称为卫星影像，不得批量抓取、预取公共瓦片或制作离线瓦片包。


收到用户或下游的检索合同，即默认授权全部检索渠道和公开搜索表面按需使用。下游只给业务目标、主体和内容需求；本工具包选择渠道、AI 使用顺序和精确词。AI→原文、原文→AI→后续计划均属常规研究。每条查询提交前冻结，范围内迭代无需另批；超出对象、目标或预算才请求裁定。权限不代表工具、登录、访问或真实渠道已验证。 规则见 `resources/retrieval_authority_current.json`，合同编译见 `tools/compile_retrieval_execution_request.py`。

## 使用边界（0.8.0-rc.4）

- 使用本人的正常账号和本机正常界面，保持合理频率；完整保留当前可见桌面研究能力。
- 不迁移、上传或交接 Cookie、token、profile、扫码凭证、本地存储、私聊、通讯录或非公开资料。
- 不绕过登录、验证码、付费墙、权限墙、风控或访问控制；出现安全确认时交由本人处理后继续。
- 依赖鼠标、键盘、窗口焦点或剪贴板的任务在同一台 Mac 上串行执行；这只是桌面冲突控制，不是授权机制。
- 引用第三方文字、图片、音视频或地图时保留必要来源与署名；OSM 图件保留可见 `© OpenStreetMap contributors`。
