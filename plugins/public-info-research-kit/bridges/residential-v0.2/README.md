# 住宅 UE v0.2 互操作桥

数据流为：

`residential.upstream_task.v0.2 → public_evidence_envelope.v1 → residential.upstream_response.v0.2 → residential.upstream_adoption_receipt.v0.2`

两个 Plugin 独立安装，不共享 cwd、绝对路径、账号态或内部实现。公开信息研究包负责渠道、检索、失败归因和证据分层；住宅 UE 负责业务充分性验收、采用／拒绝、直接竞品、价值锚点与 SC 判断。

机器锁见 `consumer-contract-lock.v0.2.json`。从公开信息 Plugin 根目录运行：

```bash
python3 tools/validate_residential_bridge.py
```

若本机另有住宅公开候选仓，可只读核对实际文件：

```bash
python3 tools/validate_residential_bridge.py --consumer-root <住宅公开候选仓>
```

通过只代表两个未发布候选包的 Schema 和脱敏 fixture 相容，不代表真实 GUI、住宅业务采用或两个版本已经正式发布。
