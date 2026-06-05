# Discover 自动记录流程

## 核心思路

你不需要再手工截图、手抄问题。每一轮只做两件事：

1. 在浏览器里把问卷切到目标状态，例如 `Fear = Yes / Scary = Often`。
2. 回到 PowerShell 按回车，让 `fill_once.py --mode discover` 自动保存截图和页面文本。

`discover` 不会点击答案，不会提交问卷。它只读取当前可见页面。

## 推荐命令模板

先进入目录：

```powershell
cd "D:\Study_Resource\社交网络安全与隐私\Xlab\age_rating_collection"
```

抓取问卷页：

```powershell
python .\fill_once.py `
  --mode discover `
  --output .\results\discover_fear_often_questionnaire.json `
  --profile-dir .\.local\playwright-profile `
  --browser-channel chrome `
  --pause-before-capture
```

脚本打开浏览器后，先不要急着回车。你在浏览器里完成目标选择：

```text
Fear = Yes
Scary elements = checked
Horrifying elements = unchecked
How frequent = Often
其他全部 No
```

确认页面状态正确后，回到 PowerShell 按回车。脚本会生成：

```text
results/discover_fear_often_questionnaire.json
results/discover_fear_often_questionnaire.png
```

然后进入 Summary 页，再抓一次：

```powershell
python .\fill_once.py `
  --mode discover `
  --output .\results\discover_fear_often_summary.json `
  --profile-dir .\.local\playwright-profile `
  --browser-channel chrome `
  --pause-before-capture
```

同样，确认浏览器显示的是 Summary 页后，回到 PowerShell 按回车。脚本会生成：

```text
results/discover_fear_often_summary.json
results/discover_fear_often_summary.png
```

## 每个探针的命名规则

用稳定英文名，后续我能直接识别：

| 探针 | 问卷页输出 | Summary 输出 |
|---|---|---|
| Fear Rare | `discover_fear_rare_questionnaire.json` | `discover_fear_rare_summary.json` |
| Fear Often | `discover_fear_often_questionnaire.json` | `discover_fear_often_summary.json` |
| Fear Horrifying | `discover_fear_horrifying_questionnaire.json` | `discover_fear_horrifying_summary.json` |
| Violence Yes | `discover_violence_yes_questionnaire.json` | `discover_violence_yes_summary.json` |

截图会自动使用同名 `.png`，不需要你手工截图。

## 你每轮实际要做什么

以 `Fear Often` 为例：

1. 运行问卷页 discover 命令。
2. 浏览器打开后，在浏览器里点好：
   `Fear = Yes`、`Scary elements = checked`、`Often`。
3. 回 PowerShell 按回车。
4. 在浏览器里点到 Summary。
5. 运行 Summary discover 命令。
6. 确认浏览器显示 Summary 后，回 PowerShell 按回车。
7. 把生成的两个 JSON 和两个 PNG 留在 `results/`，我可以继续整理。

## 注意事项

- 不点击最终 `Submit`。
- 如果出现 reCAPTCHA 或限速，脚本会停止；把结果文件发给我看。
- `discover` 只能记录当前可见页面，隐藏子问题仍需要你先把父问题点成 `Yes`。
- 每次只改一个变量，便于比较评级差异。

## 自动点击单个探针

如果你已经停在问卷页，也可以让脚本按答案 JSON 自动点击，并进入 Summary 后停止。
默认情况下，它不会点击 `Save`、`Submit` 或送审按钮。

示例：自动跑 `Horrifying elements = Yes` 探针：

```powershell
python .\fill_once.py `
  --mode run `
  --answers .\examples\fear_horrifying_only.json `
  --output .\results\run_fear_horrifying_only.json `
  --connect-cdp http://127.0.0.1:9223 `
  --allow-unverified-map `
  --confirm-authorized-test-app
```

如果 Google 在修改已存在问卷后禁用 `Next`、启用 `Save`，脚本会默认停止。
只有在确认这是隔离草稿应用、且课程允许保存草稿问卷变更时，才加：

```powershell
  --allow-save-to-summary
```

这个开关只允许点击 Play Console 的 `Save` 草稿按钮，仍然不会点击 `Submit`、`Publish`
或送审按钮。

要求：

- Chrome 已通过项目 CDP profile 打开，并且你已登录。
- 当前标签页停在内容评级 Questionnaire 页面。
- 每次只跑一个低频探针。
- 看到验证码、限速或异常时停止，不重试刷页面。

## URL 参数怎么用

最省事的方式是不传 `--url`。脚本会打开 Play Console，你在浏览器里自己进入目标页面，
然后按回车抓取。

如果你已经复制了真实地址，也可以加：

```powershell
--url "https://play.google.com/console/..."
```

不要把示例里的 `"粘贴当前问卷页面 URL"` 原样复制进去；那只是占位文字。

## 复用你已经登录的 Chrome

如果你不想在 Playwright 的专用浏览器里重新登录，可以让脚本连接到你已经登录过的
Chrome。步骤如下。

注意：新版 Chrome 对默认用户资料目录的远程调试更严格。即使命令行里出现了
`--remote-debugging-port=9222`，端口也可能没有真正监听。若 `Profile 3` 这类已有
资料目录无法监听，改用下面的“项目专用 CDP profile”。它需要登录一次，但之后会保留
登录状态。

实际结论：如果“已有 Profile 3”无法监听端口，而“复制 Profile 3 到项目目录”后又显示
未登录，这是 Chrome 的账号会话保护在生效。不要继续尝试复制 Cookie、解密登录数据或
绕过浏览器保护。此时可选方案只有两个：

- 在项目专用 CDP profile 里登录一次，之后复用它。
- 继续用你原本已登录的 Profile 3 手工操作和截图，脚本不接管该窗口。

先关闭所有 Chrome 窗口。Chrome 有时会在后台继续运行，所以先检查：

```powershell
Get-Process chrome -ErrorAction SilentlyContinue
```

如果仍然能看到 `chrome` 进程，说明远程调试参数很可能不会生效。确认没有重要页面后，
可以结束它们：

```powershell
Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process
```

然后用 PowerShell 启动带远程调试端口的 Chrome：

```powershell
& "$env:ProgramFiles\Google\Chrome\Application\chrome.exe" `
  --remote-debugging-port=9222 `
  --remote-debugging-address=127.0.0.1 `
  --profile-directory="Default"
```

如果你的账号在 Chrome 的 `Profile 1`，把 `Default` 改成 `Profile 1`。Chrome 打开后，
确认 Google Play Console 已经是登录状态。

先验证端口真的打开了：

```powershell
Invoke-WebRequest http://127.0.0.1:9222/json/version
```

如果这里报 `ECONNREFUSED` 或连接失败，说明 Chrome 没有以远程调试模式启动。通常是旧的
Chrome 后台进程没有关干净，回到上面的 `Get-Process chrome | Stop-Process` 再重开。

然后 discover 命令改成：

```powershell
python .\fill_once.py `
  --mode discover `
  --output .\results\discover_fear_often_questionnaire.json `
  --connect-cdp http://127.0.0.1:9222 `
  --pause-before-capture
```

这会在你已登录的 Chrome 会话里新开一个标签页。你进入目标问卷页、点好状态后，
回 PowerShell 按回车即可抓取。

用完后关闭这个 Chrome。远程调试端口只建议采集时临时打开。

## 项目专用 CDP profile

如果已有 Chrome Profile 无法开放端口，使用项目内的独立资料目录：

```powershell
& "$env:ProgramFiles\Google\Chrome\Application\chrome.exe" `
  --remote-debugging-port=9223 `
  --remote-debugging-address=127.0.0.1 `
  --user-data-dir="D:\Study_Resource\社交网络安全与隐私\Xlab\age_rating_collection\.local\chrome-cdp-profile" `
  "https://play.google.com/console"
```

验证：

```powershell
curl.exe http://127.0.0.1:9223/json/version
```

第一次需要在这个 Chrome 里登录 Google Play Console。登录状态会保存在
`.local/chrome-cdp-profile`，后续继续复用 9223 即可。

discover 命令：

```powershell
python .\fill_once.py `
  --mode discover `
  --output .\results\discover_fear_often_questionnaire.json `
  --connect-cdp http://127.0.0.1:9223 `
  --pause-before-capture
```
