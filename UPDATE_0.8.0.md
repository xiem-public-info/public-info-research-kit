# 更新到 0.8.0

0.8.0-rc.3 是“质量与行为同构”候选：它把研发主线中可公开、可迁移的渠道画像、检索方法、充分性、自适应增量、证据拒收、黄金样例和回归 harness 带入公开包，同时继续排除账号态、真实业务样本、内部运行状态和退役路线。

## 主要新增

- D-291 空间坐标证据：调用方对象集、单中心点、路线自动吸附、垂距、四至尽力提供、相对便利性和仅实际使用 OSM 资产时署名；不代下游绘图。
- `CAPABILITY_MATRIX.md` 与 Plugin 内渠道画像：每个渠道擅长、不擅长、黄金方法、失败类型和停止线。
- D-235 社媒语义查询核心与深化后的 `social_query_plan.v1`。
- D-292 可移植研究编排：双平台聚合表面独立、住宅竞品生命周期前置、项目事件与全局家庭旅程双计数、首次回传主动判断统一语义核、官方必要原话与自然收线后换线程。
- 微信 AI 搜索按 D-293 从收到的检索合同继承权限；任务权限、执行就绪与真实 GUI 验收分别检查。
- D-237／D-240／D-241 充分性、增量授权、边际信息增益和查询晋升合同。
- 五类证据、软证据拒收、上下游状态隔离，以及 `negative_hits / conflicts / gaps / stop_reason` 保留。
- 5 个脱敏黄金任务、4 组负例、决策手册与统一离线 harness。
- 默认离线、只读 doctor 和逐机 smoke 回执；Computer Use、macOS 权限和账号登录均由终端用户自行处理。
- 住宅 UE v0.2 双包 Schema 锁和双向 conformance。

## 更新后检查

1. 新建一个 Codex 任务，确认七个 Skill 可见。
2. 按 `INSTALL_CHECKLIST.md` 核对需要的能力。
3. 可选运行 `python3 plugins/public-info-research-kit/tools/doctor.py --channel all`。
4. 每台电脑按 `SMOKE_TESTS.md` 对所需渠道完成最小真实 smoke。

## 重要边界

RC 离线回归、安装可见、doctor、真实渠道 smoke、住宅双包兼容和业务接受分别验收。候选通过不等于正式发布；微信 AI 离线 Gate 不等于 live 能力；微信／小红书 fixture 不等于真实平台已执行；住宅 UE Schema 相容不等于住宅业务采用。
