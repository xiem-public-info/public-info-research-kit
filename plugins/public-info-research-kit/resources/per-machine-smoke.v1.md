# 每台电脑最小真实 smoke

离线 harness 证明合同和拒收规则可执行；每台电脑仍需用自己的账号、插件、权限和可见界面完成最小真实 smoke。一次 smoke 只验证一个渠道，不验证业务效果。

## 状态分层

1. `installed_visible`：公开信息研究包已安装，七个 Skill 可见。
2. `doctor_checked`：doctor 完成只读检查；它不安装 Computer Use、不改权限、不操作登录。
3. `gui_prerequisites_confirmed`：仅 GUI 渠道，由终端用户确认 Computer Use、macOS 权限、本人账号登录和共享桌面空闲。
4. `real_channel_smoke_passed`：完成下面对应渠道的最小真实任务。
5. `business_acceptance`：由实际业务任务另行判断；smoke 回执必须保持 `not_assessed`。

## 普通公开网页 smoke

- 选择一条无需登录的具名公开网页。
- 打开原页，读取至少一项可见事实候选并保留一个稳定来源指针。
- 不要求 Computer Use，不把搜索摘要或转载当原文。

## 微信 smoke

- 终端用户自行确认 Computer Use 已安装启用并有权限，登录自己的微信，首次手动打开公开搜一搜。
- 冻结一个非敏感、低风险精确查询；只输入一次、可见逐字确认后只提交一次。
- 至少打开 1 篇公开文章，正文推进至少 2 次，每次依据最新可见画面判断。
- 安全关页；不互动、不发布、不读取私聊或通讯录。
- 画面有歧义、登录／验证码／风控或不可读时停止，记录失败，不通过重复动作“做成成功”。

## 小红书 smoke

- 终端用户自行确认 Computer Use 已安装启用并有权限，在自己的正常可见 Chrome 中登录小红书。
- 冻结一个非敏感、低风险精确查询；只输入并提交一次。
- 至少打开 1 条公开笔记，读取至少一种实际可见内容：正文、字幕、画面文字或可见评论，并保留稳定指针。
- 安全退出详情；不点赞、不收藏、不评论、不关注、不发布。
- 出现调试／自动化提示、异常 profile、登录／验证码／风控或页面不明时立即停止，不切换到 DOM、CDP、Playwright 或隔离 profile。

## 回执

把结果写成 `per_machine_smoke_receipt.v1`，运行：

```bash
python3 tools/validate_per_machine_smoke.py --input <smoke-receipt.json>
```

回执只记录完成条件、计数、状态和边界，不保存查询原文、账号名、截图、Cookie、token、profile 路径或客户数据。验证通过只代表这一台电脑、这一渠道、这一次 smoke 通过。
