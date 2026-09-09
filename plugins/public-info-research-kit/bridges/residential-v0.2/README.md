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

## rc.7 原请求与实际执行绑定

住宅 Owner 冻结原 `request.json`；上游只读消费。编译器映射完整验收条件、对象、停止和授权字段，保存原请求副本和 canonical SHA-256（UTF-8、`ensure_ascii=False`、`sort_keys=True`、`separators=(',', ':')`）。冻结后进度写在其他文件，不修改原请求。

实际充分性包须包含 `request_id`、`task_id`、`source_request_sha256` 、完整原验收条件及本批次实际 `execution_request`。新回包增加 `contract_binding`：原请求 schema/编号/哈希、原验收合同副本和实际充分性包的 canonical SHA-256。模式、数量、质量、资格或多样性漂移均须订正上游映射，不能回改原合同迎合结果。

```bash
python3 tools/package_evidence.py --input draft.json --request request.json --sufficiency-input sufficiency-input.json --output new-envelope.json --receipt packaging-receipt.json
python3 tools/validate_public_evidence.py --input new-envelope.json --request request.json --sufficiency-input sufficiency-input.json
```

上游在本任务已获准的工作目录生成新包，住宅 Owner 接入回包并生成自己的 `response.json`、`adoption.json`。不得因合作关系或检索授权就改写另一个任务的文件；真实写入按当前授权与工具权限。审核拒绝时先核拒绝内容和既有授权，不换路径或写法绕过审核。条件采用是业务 Owner 的决定，不能写成真人验收。

新增范围内迭代与超范围扩展分开处理，`in_scope_iteration_allowed=false` 优先。旧任务恢复回读其明确停止要求，不自动改授权。后续扩展获授权时，把完整独立采用回执放在执行请求与充分性包的 `continuation_adoption` 中，另用同一 `continuation_binding` 绑定原请求哈希、采用回执哈希、原文 limits 与预算。不得向住宅 rc.8 的原采用回执或 incremental_decision 增加字段。具体字段和模型解释边界见 `skills/public-info-intake-router/SKILL.md`；检查同一任务、住宅 Owner、批准查询与明确预算，原请求仍不变。记录有权 Owner 的真实决定，不为通过检查补造授权。

旧包保留，含旧 rc.6 绑定的只读审阅用 `--historical-read-only`，结果不具有生产绑定通过状态；更早无绑定结构也可显式 `--allow-legacy-unbound`；旧包未绑定不能直接进入新版采用。旧成果可依据原请求和实际证据另生成新包，缺失原回执则如实保留缺口。测试入口 `tests/run_request_contract_binding.py` 使用虚构请求先冻结、再编译和封装；不从回包反建原请求。


实际调用前使用 `compile_retrieval_execution_request.py --task request.json --check-execution execution.json`，充分性包携带同一实际执行请求。住宅 rc.8 的 Schema 原文件及消费实现保持不变，证据外壳哈希仍为锁文件中的值；新授权绑定仅进入已被外壳指纹覆盖的实际充分性输入。

在完整上游仓库根目录，用已安装 jsonschema 的 Python 运行跨包检查：

```bash
python3 scripts/verify_residential_rc8_conformance.py --producer plugins/public-info-research-kit --consumer <未修改的住宅rc8完整目录> --output <检查报告.json>
```

该检查使用住宅包自带的虚构冻结请求，从编译、实际执行检查、充分性封装到住宅原消费器，核对四份实际 JSON Schema。原住宅 rc.8 的旧检查脚本仍按当时夹具运行；其缺实际执行请求的旧夹具不能直接证明 rc.7 生产通过，使用上述入口完成新版联动。
