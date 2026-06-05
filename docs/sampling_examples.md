# 采样示例说明

## 目的

本文件补充 1 号任务的“采样策略”交付物，给 2 号提供一组可以直接审计和试跑的
示例输入。这里的样本是**问卷答案输入**，不是实际采集结果；真实评级结果需要由
`fill_once.py --mode run` 到 Summary 后生成。

## 核心示例

| 文件 | 用途 |
|---|---|
| `examples/all_no.json` | 全 No 锚点，用于最低风险基线和回归测试 |
| `examples/all_yes.json` | 全 Yes 锚点，用于高风险边界探针；当前地图未完全验证，正式运行前需谨慎 |
| `examples/random_001.json` | 当前地图下的 balanced random 示例 |
| `examples/result_001.json` | 输出 JSON 结构示例 |

以上三个输入样例已经通过当前 `questionnaire_map.json` 的离线审计。隐藏问题会解析为
`N/A`，不会被错误当作 `No`。

## 预览采样包

已额外生成一组小规模采样预览，目录为：

```text
examples/sampling_preview/
```

生成命令：

```powershell
python .\generate_samples.py `
  --count 10 `
  --seed 20260603 `
  --out-dir .\examples\sampling_preview `
  --allow-unverified-map
```

`manifest.json` 中的比例为：

| strategy | 数量 |
|---|---:|
| `no_biased` | 3 |
| `yes_biased` | 2 |
| `balanced_random` | 5 |

同时生成了两个锚点：

- `examples/sampling_preview/all_no.json`
- `examples/sampling_preview/all_yes.json`

这正好对应正式 1000 条时的比例设计：

| strategy | 1000 条目标数量 |
|---|---:|
| `no_biased` | 300 |
| `yes_biased` | 200 |
| `balanced_random` | 500 |

## 为什么不是重复 300 条全 No、200 条全 Yes

课程口径里的“30% 全 no、20% 全 yes、50% 随机组合”如果字面理解为重复同一条
`all_no` 300 次、`all_yes` 200 次，会产生大量重复样本，对建模没有帮助。

因此本项目落地为：

- `all_no`、`all_yes`：只作为锚点和回归测试样本保留少量。
- `no_biased`：大多数题倾向 `No`，但保留少量随机翻转。
- `yes_biased`：大多数题倾向 `Yes`，但保留少量随机变化。
- `balanced_random`：对当前可见题按固定随机种子生成答案。

这样既保留课程要求的低风险/高风险/随机三类覆盖，又避免重复行凑数。

## 2 号使用建议

正式采集前，2 号应先小批量试跑 `examples/sampling_preview/`，确认：

1. `fill_once.py` 可以稳定进入 Summary。
2. 输出 JSON 的 `status` 为 `summary_reached`。
3. `canonical_hash` 不重复。
4. `summary.raw_text` 中包含全部地区评级。
5. 遇到验证码、限速或页面结构变化时，脚本会停止并保留记录。

如果 `generated_answers/manifest.json` 提示唯一组合不足，说明问卷地图还不够完整，
应先补全子树，不要用重复样本凑满 1000 条。
