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

通过只代表接口和脱敏样例相容，不代表真实 GUI、住宅业务采用或用户验收。版本发布状态另看对应 Release。

## rc.6 请求绑定

住宅 Owner 冻结原 `request.json`；上游只读消费。编译器映射完整验收条件、对象、停止和授权字段，保存原请求副本和 canonical SHA-256（UTF-8、`ensure_ascii=False`、`sort_keys=True`、`separators=(',', ':')`）。冻结后进度写在其他文件，不修改原请求。

实际充分性包须包含 `request_id`、`task_id`、`source_request_sha256` 及完整原验收条件。新回包增加 `contract_binding`：原请求 schema/编号/哈希、原验收合同副本和实际充分性包的 canonical SHA-256。模式、数量、质量、资格或多样性漂移均须订正上游映射，不能回改原合同迎合结果。

```bash
python3 tools/package_evidence.py --input draft.json --request request.json --sufficiency-input sufficiency-input.json --output new-envelope.json --receipt packaging-receipt.json
python3 tools/validate_public_evidence.py --input new-envelope.json --request request.json --sufficiency-input sufficiency-input.json
```

上游在本任务已获准的工作目录生成新包，住宅 Owner 接入回包并生成自己的 `response.json`、`adoption.json`。不得因合作关系或检索授权就改写另一个任务的文件；真实写入按当前授权与工具权限。审核拒绝时先核拒绝内容和既有授权，不换路径或写法绕过审核。条件采用是业务 Owner 的决定，不能写成真人验收。

新增范围内迭代与超范围扩展分开处理，`in_scope_iteration_allowed=false` 优先。旧任务恢复回读其明确停止要求，不自动改授权。后续扩展获授权时，把独立采用回执放在充分性包的 `continuation_adoption` 中；检查同一任务、住宅 Owner 和被批准查询的范围，原请求仍不变。记录有权 Owner 的真实决定，不为通过检查补造授权。

旧包保留，只读检查需显式 `--allow-legacy-unbound`；旧包未绑定不能直接进入新版采用。旧成果可依据原请求和实际证据另生成新包，缺失原回执则如实保留缺口。测试入口 `tests/run_request_contract_binding.py` 使用虚构请求先冻结、再编译和封装；不从回包反建原请求。
