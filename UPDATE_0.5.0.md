# 更新与验收 0.5.0

## 已安装 0.3.x 或 0.4.0

优先在 Codex 的 Plugin 页面点击更新，不需要先卸载。若应用内更新失败，再使用：

```bash
codex plugin marketplace upgrade public-info-research-public && codex plugin add public-info-research-kit@public-info-research-public
```

更新后新建一个任务，不需要重启 Codex。确认：

- Plugin 版本为 0.5.0；
- 七个 Skill 均可见；
- 旧版 0.3.x 不再启用。

## 全新电脑或全新 Codex 账号

打开 <https://github.com/xiem-public-info/public-info-research-kit>，在 Codex 中安装仓库里的 `public-info-research-kit` Plugin。没有出现安装卡片时，直接对 Codex 说：“安装这个 GitHub 仓库里的 public-info-research-kit Plugin。”

## 微信最小验收

1. 本人登录微信桌面版。
2. 本人手动打开“搜一搜”页面并保持在前台；不依赖快捷键。
3. 新建 Codex 任务并发送：

> 使用 public-info-research-kit 的微信研究能力，以研究者视角检索“成都住房消费提振措施”。先说明主体识别与查询设计，再提交一个精确检索词；从公开文章结果中阅读一篇可读文章，返回标题、账号、日期、主要判断、事实边界，并说明查询停留门是否通过。不要读取私聊，不绕过登录或安全提示。

验收通过标准：成功进入公开搜索、提交精确词、获得结果列表、打开并读完一篇文章；报告能区分检索词设计、内容供给和原文证据。需要扫码、重新登录或安全确认时由本人处理，完成后让 Codex 继续。
