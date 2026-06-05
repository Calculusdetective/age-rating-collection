# Google Play Game Age Rating Collection Starter Kit

本目录是课程项目中“1 号：数据采集设计”的交付包。目标是摸清 Google Play
Console 中 `Game` 内容评级问卷的树状结构，并为 2 号提供一次填写、读取 Summary
结果和生成采样输入的基础工具。

## 安全边界

- 只使用自有账号中单独创建的、未发布的草稿测试应用。
- 当前自动化权限尚未由课程明确确认。权限确认前，只运行离线审计和只读侦察。
- `fill_once.py` 默认不会点击最终 `Submit`、发布或送审按钮。
- 发现 reCAPTCHA、限速或页面结构变化后，脚本截图、写入状态并停止。
- 不实现验证码绕过、代理轮换、浏览器指纹伪装或账号密码自动填写。
- 问卷答案必须用于课程授权的隔离实验，不要对真实应用随机提交答案。

## 当前状态

`questionnaire_map.json` 已根据 2026-06-03 的全 `No` 手工截图确认了当前可见的
`Game` 顶层问题。`Yes` 分支尚未全部探索，因此正式批量采样仍应保持暂停。
全 `No` 评级基线见 `docs/baseline_all_no.md`。

## 环境准备

推荐先在 Windows 上侦察和调试：

```powershell
cd .\age_rating_collection
python -m pip install -r requirements.txt
python -m playwright install chromium
```

Playwright 已安装时仍可能缺少浏览器内核。如果希望复用本机 Chrome，可以在浏览器
命令后加 `--browser-channel chrome`。

不要把登录状态目录提交给其他人：

```text
.local/playwright-profile/
```

## 第一步：离线校验

离线审计不会打开浏览器。先用它确认树结构、隐藏节点 `N/A` 规则和样例输入格式：

```powershell
python .\fill_once.py `
  --mode audit `
  --answers .\examples\random_001.json `
  --output .\results\random_001.audit.json
```

运行测试：

```powershell
python -m unittest discover -s .\tests -v
```

## 第二步：只读侦察

1. 在 Play Console 中创建独立的未发布草稿应用。
2. 手工进入该应用的内容评级问卷页面。
3. 复制该页面 URL。
4. 运行：

```powershell
python .\fill_once.py `
  --mode discover `
  --output .\results\discover_001.json `
  --profile-dir .\.local\playwright-profile `
  --browser-channel chrome `
  --pause-before-capture
```

浏览器会保持可见。需要登录时请手工完成。加上 `--pause-before-capture` 后，
你可以先在浏览器里把页面点到目标状态，再回到 PowerShell 按回车自动抓取。
`discover` 模式只读取当前页面可见控件，不会点击任何答案。更详细的流程见
`docs/discover_workflow.md`。

如果要复用你已登录的本机 Chrome，不想在 Playwright 专用资料目录里重新登录，请按
`docs/discover_workflow.md` 中“复用你已经登录的 Chrome”一节使用 `--connect-cdp`。

## 第三步：单次填写

只有在课程明确允许对隔离测试应用进行低频自动化后，才运行：

```powershell
python .\fill_once.py `
  --mode run `
  --answers .\examples\random_001.json `
  --output .\results\random_001.json `
  --profile-dir .\.local\playwright-profile `
  --url "粘贴隔离草稿应用的问卷 URL" `
  --browser-channel chrome `
  --confirm-authorized-test-app
```

`run` 模式默认要求问卷地图中的每个节点均已人工确认。首次校准可以临时添加
`--allow-unverified-map`，但不要把校准结果视为正式数据。脚本到达 Summary 后保存
原始文本和截图，随后停止，不点击最终提交按钮。

## 第四步：生成采样输入

问卷地图完整验证后，生成去重答案：

```powershell
python .\generate_samples.py `
  --count 1000 `
  --seed 20260602 `
  --out-dir .\generated_answers
```

脚本采用 `30% No-biased + 20% Yes-biased + 50% Balanced random`，并额外生成
`all_no.json` 和 `all_yes.json` 回归锚点。每条路径以实际可见问题及答案生成
`canonical_hash`，隐藏节点不会错误地当作 `No`。

如果 `manifest.json` 提示可达唯一路径不足，应先补全问卷树或调整采样设计，不能用
重复样本凑到 1000 条。

## 输入输出

输入 JSON：

```json
{
  "sample_id": "random_001",
  "strategy": "balanced_random",
  "answers": {
    "violence.exists": "no",
    "fear.contains_disturbing_content": "yes"
  }
}
```

输出 JSON 会保留：

- 实际解析后的答案，隐藏题为 `N/A`
- 按可见路径生成的 `canonical_hash`
- 运行状态和错误信息
- Summary 原始文本
- 保守提取的地区评级提示
- 页面截图路径

首次正式运行后，请用手工结果逐项比对 Summary，并校准 `selectors.json` 和
`parse_summary()`。在解析器稳定前，`raw_text` 是唯一可信来源。

## 交接清单

交给 2 号：

- `docs/member2_operation_template.md`
- `fill_once.py`
- `generate_samples.py`
- 已人工验证的 `questionnaire_map.json`
- 校准后的 `selectors.json`
- `docs/sampling_strategy.md`
- `docs/sampling_examples.md`
- 至少三个手工与脚本交叉验证过的结果：全 No、全 Yes、随机路径

交给表达组：

- `docs/questionnaire_map.md`
- `docs/script_flow.md`
- `docs/sampling_strategy.md`
- `docs/sampling_examples.md`
- `docs/recaptcha_recon.md`

## 官方文档

- [内容评级问卷与评级结果](https://support.google.com/googleplay/android-developer/answer/9859655?hl=en)
- [创建应用](https://support.google.com/googleplay/android-developer/answer/9859152?hl=en)
- [开发者账号设置](https://support.google.com/googleplay/android-developer/answer/6112435?hl=en)
