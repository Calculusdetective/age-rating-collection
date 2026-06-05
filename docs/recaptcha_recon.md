# reCAPTCHA 与可采集性侦察记录

## 当前结论

截至 2026-06-03，本项目在低频、人工监督的测试中**尚未遇到 reCAPTCHA**，
也未观察到明显限速页面。

这个结论只说明当前课程测试规模下可以继续做低频采集设计验证，不代表适合无人值守、
高频或大规模自动化采集。后续 2 号执行批量采集时仍应保留人工监督、间隔控制和失败记录。

## 测试环境

| 项目 | 内容 |
|---|---|
| 平台 | Google Play Console |
| 问卷分支 | Content ratings / Game |
| 应用 | 自有账号下的隔离未发布草稿应用 |
| 浏览器 | Chrome，项目专用 CDP profile |
| 自动化方式 | Python + Playwright |
| 提交策略 | 停在 Summary，不点击最终 Submit、Publish 或送审按钮 |
| 账号策略 | 不在代码中保存账号密码；必要时人工登录 |

## 已完成侦察

| 日期 | 操作模式 | 操作内容 | 是否出现 reCAPTCHA | 是否限速 | 证据文件 | 备注 |
|---|---|---|---|---|---|---|
| 2026-06-03 | 手工 | 创建/进入隔离草稿应用，手工走通 Game 问卷全 No | 否 | 否 | `screenshots/问卷全no.png`、`screenshots/全no对应评级.png` | 首次人工基线 |
| 2026-06-03 | 手工 | `Fear = Yes / Scary elements = Rare` | 否 | 否 | `screenshots/仅fear_yes.png`、`screenshots/fear_yes评级.png` | 手工探针 |
| 2026-06-03 | discover | 抓取 `Fear = Yes / Scary elements = Often` 问卷页与 Summary 页 | 否 | 否 | `results/discover_fear_often_questionnaire.json`、`results/discover_fear_often_summary.json` | 只读 DOM/文本侦察 |
| 2026-06-03 | run | 自动填写 `Horrifying elements = Rare` 并读取 Summary | 否 | 否 | `results/run_fear_horrifying_only.json` | 低频单次自动化 |
| 2026-06-03 | run | 自动填写 `Horrifying elements = Often` 并读取 Summary | 否 | 否 | `results/run_fear_horrifying_often.json` | 低频单次自动化 |

## 脚本中的保护措施

`fill_once.py` 已加入验证码和限速检测逻辑。脚本会检查：

- `iframe[src*='recaptcha']`
- `.g-recaptcha`
- `[data-sitekey]`
- `iframe[title*='reCAPTCHA']`
- 页面文本中的 `reCAPTCHA`
- 页面文本中的 `I'm not a robot`
- 页面文本中的 `Verify you are human`
- 常见限速提示，如 `Too many requests`、`Try again later`、`Rate limit`

如果检测到这些标记，脚本会：

1. 截图保存当前页面。
2. 在结果 JSON 中写入 `captcha_detected` 或 `rate_limited` 状态。
3. 立即停止。
4. 不尝试破解验证码、不自动刷新、不切换 IP、不做浏览器指纹伪装。

## 对 2 号批量采集的建议

当前判断：**可做低频、人工监督的小规模采集试运行；不建议直接无人值守跑 1000 条。**

建议执行策略：

- 每次只使用隔离草稿应用。
- 保持可见浏览器运行，方便人工观察异常。
- 使用持久化登录状态，不在脚本中写账号密码。
- 单次采集到 Summary 后停止，不点击最终 Submit、Publish 或送审。
- 每条结果保留原始 `summary.raw_text`、截图和状态码。
- 遇到验证码、限速、登录异常或页面结构变化，立即停止并记录。
- 如果验证码开始频繁出现，应暂停自动化实验，向老师申请明确授权或受控环境。

## 给全组的可采集性结论

```text
在 2026-06-03 的低频测试中，Google Play Console 内容评级问卷未出现 reCAPTCHA，
也未观察到限速。手工填写、只读 discover、低频单次 run 均可到达 Summary。

脚本已设置验证码与限速检测：一旦检测到 reCAPTCHA、I'm not a robot、
Verify you are human、Too many requests 等标记，会截图并停止，不尝试绕过。

因此，本项目可以继续采用“人工监督 + 低频自动化 + Summary 读取”的采集方案。
但不建议无人值守高频批量运行；2 号正式采集前应先小批量试跑，并保留失败样本记录。
```

## 未做的事情

- 未绕过验证码。
- 未使用代理、IP 轮换或指纹伪装。
- 未自动输入账号密码。
- 未点击最终 Submit、Publish 或送审按钮。
- 未证明 Google Play Console 在大规模高频采集下不会触发风控。
