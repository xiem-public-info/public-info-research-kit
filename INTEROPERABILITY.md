# 下游工程互操作口径（0.8 候选）

公开信息研究包与住宅 UE 等下游工程按以下单向证据接口协作：

`下游研究请求 → public_evidence_envelope.v1 → 下游响应与采用回执`

- 下游拥有业务问题、验收条件、直接竞品／价值锚点／销售沟通等业务判断，以及最终采用或拒绝决定。
- 公开信息研究包拥有渠道画像、查询冻结、渠道执行、失败归因、证据分层和上游打包。
- `public_evidence_envelope.v1` 必须保留 `request_id`、可空但不可省略的 `project_id`、`negative_hits`、`conflicts`、`gaps` 和 `stop_reason`。
- 上游状态允许 `fulfilled`、`partial`、`gap`、`stopped`；它们均不等于下游接受。
- 上游包中的 `downstream_acceptance` 固定为 `status=not_assessed`、`decided_by=null`。下游在自己的采用回执中记录接受、附条件接受或拒绝。
- 没有冲突或缺口时分别使用 `conflicts: []`、`gaps: []`，不得省略或写 `null`。
- 软证据、平台观察、冲突和缺口不得在跨工程传递中升级为硬事实。

机器可读接口清单位于 `plugins/public-info-research-kit/schemas/public_interop_manifest.v1.json`。SHA-256 按 Schema 文件原始字节计算，命令为：

```bash
shasum -a 256 plugins/public-info-research-kit/schemas/public_evidence_envelope.v1.json
```

从插件目录执行最小一致性检查：

```bash
python3 tests/run_public_evidence_contract.py
python3 tests/run_release_harness.py
```

通过离线一致性检查不代表终端电脑已完成微信／小红书真实 smoke，也不代表下游业务验收通过。

## 住宅 UE v0.2 候选锁

住宅公开候选 `codex/v0.2.0-rc.1-production-path@0a0c08eefc5ba4d5d36e9b5658ea648c44628585` 已完成双向 conformance。三个消费者 Schema 的 raw-byte SHA-256 为：

- `residential.upstream_task.v0.2`：`12f7ed916755bc37a870a6eb893210cc7e0fbc35ecea443f8e8d10bbe102b271`
- `residential.upstream_response.v0.2`：`baec010a6a21b44a0f80a9639680fc2dcda2b6bce685d28d8cd29df9dc7ed2e1`
- `residential.upstream_adoption_receipt.v0.2`：`64183f6485ac5fc8c076f7969c3d5bfd07209632a9c9ddd532c6eef7ad2e1414`

公开信息侧从 Plugin 根目录运行 `python3 tools/validate_residential_bridge.py` 验证锁；有住宅候选仓时增加 `--consumer-root <仓目录>` 核对真实文件。双方当前仍是未发布候选，真实 GUI 与业务接受均未验证。
