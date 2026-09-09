# 从 rc.6 升级到 rc.7，并保留旧成果

rc.7 补齐原请求、实际执行和充分性回传之间的检查。它保持住宅公开 rc.8 的接口文件与采用回执格式，不要求升级住宅包。rc.6 标签、下载包和历史成果保留。

只有固定 rc.7 Release 与标签公开后，才执行以下安装步骤。没有公开资产时继续使用原版，不安装浮动候选分支。

## 先识别已安装版本

优先在 Codex 的 Plugin 页面核对本插件。CLI 可只读查看：

```bash
codex plugin list --json
codex plugin marketplace list --json
```

只检查 `public-info-research-kit@public-info-research-public`。区分 installed 与 available，记录旧版本、来源引用和返回的实际目录；不要在报告中带出其他插件配置或账号信息。实际目录以工具返回为准，不假定固定缓存路径。

若用户曾把自定义配置或任务成果放进安装目录，先在受控本机位置另存这些文件及旧完整包。常规项目成果保留在原项目目录。保护恢复所需的本插件配置，不导出账号态，也不批量备份或改写整个 Codex 配置。

## 取得并安装固定版本

先核对 [rc.7 发布页](https://github.com/xiem-public-info/public-info-research-kit/releases/tag/v0.8.0-rc.7) 的 ZIP 和 SHA256SUMS。完整 ZIP 解压到新的版本目录，保留旧目录，逐项核对 `PUBLIC_BETA_MANIFEST.json` 中的文件大小和 SHA-256；哈希不符时重新取得同一固定资产，停止使用损坏副本。

首次安装按 [中文安装说明](RC_INSTALL_0.8.0.md)。已有安装时优先使用当前 Plugin 页面提供的更新功能，随后核对实际版本。CLI 的 `marketplace upgrade public-info-research-public` 只刷新登记的 Git 快照；旧引用仍是 rc.6 时，刷新不会切到 rc.7。官方说明没有保证重复 `marketplace add --ref` 会替换既有引用，也没有保证对已安装插件再次 `plugin add` 必然替换缓存，必须核实际返回。[Codex CLI 官方参考](https://learn.chatgpt.com/docs/developer-commands?surface=cli)

若当前客户端无法调整旧引用或更新实际插件，完成上述保护后，可以只移除本插件和本市场，再登记固定版本。先逐条确认本机帮助支持，逐条执行并查看结果：

```bash
codex plugin remove public-info-research-kit@public-info-research-public --json
codex plugin marketplace remove public-info-research-public --json
codex plugin marketplace add https://github.com/xiem-public-info/public-info-research-kit.git --ref v0.8.0-rc.7 --json
codex plugin add public-info-research-kit@public-info-research-public --json
```

移除插件会删除其本地配置和缓存，因此必须先保护用户放在其中的文件。不要手动删除缓存、操作其他市场，或重复卸载来碰运气。重装后只恢复用户自定义内容，不把旧执行代码覆盖到新版目录。

## 核实实际加载的版本

安装结果中的 `version` 应为 `0.8.0-rc.7`。从其 `installedPath` 读取 `.codex-plugin/plugin.json`，并在该插件目录运行：

```bash
python3 tools/compile_retrieval_execution_request.py --help
python3 tests/run_execution_request_binding.py
python3 tests/run_request_contract_binding.py
```

帮助须包含 `--check-execution`；实际安装目录的两组定点检查合计 64 项。完整发行回归在完整解压根目录运行 `python3 plugins/public-info-research-kit/tests/run_release_harness.py`，当前为 18 组、346 项；该完整包检查会扫描仓库布局，不在缺仓库根目录的插件缓存中运行。完整解压包的清单用于核文件完整性；安装目录中的关键工具文件还应与已校验完整包内对应文件一致，尤其是编译器、请求合同、充分性检查和证据校验器。

`installedPath` 不保证包含仓库根目录。doctor 当前从插件目录上两级寻找 `PUBLIC_BETA_MANIFEST.json`，适用于完整仓库/ZIP 布局；若客户端只复制插件子目录，缺这份根清单是布局差异，应按上一段核实际代码。不得仅凭 `manifest_missing` 判定损坏并反复卸载，也不能仅凭目录版本号认定代码更新完成。

新建任务后确认公开任务路由、网页与官方来源、微信已知链接、微信公开研究、小红书可见研究、地图空间证据、公开证据交付七项能力可见。安装和离线回归不启动真实检索。

## 旧任务和回退

旧原请求、回包、冲突和缺口保持原文件。旧 rc.6 带绑定回包可通过 `validate_public_evidence.py --historical-read-only` 审阅；已有原请求和充分性输入时一并传入核对。结果不会成为新版生产绑定通过。缺实际执行请求的旧材料可作历史证据，不能伪造执行记录后重新采用；恢复研究按原停止要求与新的有效决定处理。

升级失败时保留新版诊断和所有业务成果，回到保留的旧完整目录即可恢复文件级使用。若已改变 Codex 插件安装，按相同的单插件步骤安装固定 `v0.8.0-rc.6`，恢复本插件所需用户配置，并核对返回版本和实际目录；不要把 rc.7 新回包自动交给旧版生产处理。

固定回退资产：[rc.6 ZIP](https://github.com/xiem-public-info/public-info-research-kit/releases/download/v0.8.0-rc.6/public-info-research-kit-0.8.0-rc.6.zip)。SHA-256：`c752f527f1b88f83c77221e9a7dff2ffa8c99c1037977114067db1e10522eb9d`。

本轮验证范围是离线代码、两包原接口及隔离文件升级/损坏/回退。没有在用户实际 Codex 缓存或其他电脑完成安装更新；这些状态须由目标电脑按实际结果回报。
