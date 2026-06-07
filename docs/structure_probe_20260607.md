# 2026-06-07 问卷结构探针记录

本轮目标是继续摸清 Google Play Console `Game` 内容评级问卷的条件结构。操作仅停留在 Category/Questionnaire 页面，不点击最终 `Submit`，不发布、不送审。

## 方法

- 使用项目内 `.local/chrome-cdp-profile` 启动可接管 Chrome。
- 进入隔离草稿应用 `Content ratings -> Game -> Questionnaire`。
- 每次先恢复顶层全 `No`，再只打开一个父条件。
- 抓取 DOM 中所有非空 `QUESTION` 节点、可见 radio/checkbox、截图和页面文本。
- 结果保存在本地 `results/structure_probe_20260607_refined/`，该目录已加入 `.gitignore`，不建议公开推送。

## 结构扩展结果

`questionnaire_map.json` 已从原来的 53 个节点扩展到 120 个节点。

按 section 统计：

| Section | 节点数 |
|---|---:|
| Violence, Blood, or Gory Images | 28 |
| Fear | 6 |
| Sexuality, Suggestiveness, or Dating Games | 22 |
| Gambling Themes, Simulated Gambling, or Real Gambling | 8 |
| Language | 9 |
| Controlled Substance | 20 |
| Crude Humor | 5 |
| Digital Purchases, Cash Convertible Rewards, or NFTs | 10 |
| Miscellaneous | 12 |

## 关键新增发现

- `Fear -> Horrifying elements -> Often` 会新增：
  `Is there an intense and unrelenting sense of imminent threat?`
- `Violence -> non-humans` 会新增 setting、style、reaction、presentation、blood/gore、human-like response、real-world animals、dark overtones 等题。
- `Violence -> gory without violence` 会新增 explicit detail level。
- `Violence -> unrelated blood` 会新增 blood amount/frequency 题。
- `Sexuality` 的 `sexual activity`、`suggestive themes`、`dating games`、`nudity/revealing outfits`、`sexual violence refs` 均有更深题。
- `Gambling themes`、`playable bingo`、`casino/betting` 会追加 prominence 或 cash reward 相关题。
- `Language` 四类子项会追加 frequency 题。
- `Controlled Substance` 会根据 drug/alcohol/tobacco 类型追加 reference/use/glamorize/detail/frequency 题。
- `Crude Humor = Yes` 会追加四类 bodily functions checkbox。
- `Digital Purchases = Yes` 会追加 digital goods、cash convertible rewards、transferable assets，并继续展开 loot box、trade system、marketplace、purchase requirement 等题。
- `Miscellaneous -> user interaction = Yes` 会追加 block/report/moderation/friends-only 四个安全机制题。
- `Miscellaneous -> realistic crimes = Yes` 会追加 imitation risk 和 detailed technique 两题。

## 当前限制

`questionnaire_map.json` 当前结构校验通过，但严格校验仍有 54 个 `children_explored=false`。这些多为深层 leaf 或选项节点，原因是 Google Play 问卷要求从上到下完成前置兄弟题后，后面的控件才允许切换。今天已经确认它们可见，但没有把每个 leaf 的 `Yes`/每个选项都逐一切换到终点。

因此结论是：

- 可以用于表达组说明“问卷结构已显著补全”。
- 可以用于 2 号理解采集难度和继续补探针。
- 仍不建议直接放量跑 1000 条。
- `generate_samples.py` 保持严格模式，仍会阻止正式批量生成，直到剩余 leaf 探针确认完毕。

## 安全结论

本轮未观察到 reCAPTCHA 或限速提示。若后续在高频探针或 Summary 读取中出现验证码、限速或页面结构变化，应立即停止，记录截图，不做验证码绕过。
