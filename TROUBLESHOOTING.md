# Troubleshooting

安装成功后直接使用。只有安装失败、Plugin 不可见或运行环境异常时，才运行：

```bash
python3 plugins/public-info-research-kit/tools/doctor.py
```

doctor 会一次汇总全部关键缺口，不会逐项失败后要求反复重跑。

- `python_unsupported`：安装 CPython 3.12、3.13 或 3.14。
- `node_missing` / `npm_missing`：仅开发或本地 fixture 需要；普通使用可忽略。
- `proxy_detected`：确认终端与 Codex 使用同一可信代理策略；doctor 不显示代理值。
- `tls_probe_failed`：检查系统时间、证书链或代理 TLS 配置，不要关闭证书校验。
- `codex_cli_missing`：在 Codex 应用设置中确认命令行工具可用。
- `marketplace_missing` / `plugin_missing`：先在 Plugin 页面重新安装；仍未刷新时新建任务；只有继续不可见时才重启 Codex 排错。
- `skill_count_mismatch`：确认安装的是 0.4.0，且 Plugin 中包含七个 Skill。
- 微信或小红书出现登录、安全、验证码、风控或页面不明：由本人在原应用中处理，完成后继续，不切换到绕过路线。

可复现的安装、更新或 Plugin 故障可按 `SUPPORT.md` 提交；具体研究任务不提供一步一步辅导。
