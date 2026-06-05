# 采样策略说明

## 目标

课程要求采集至少 1000 个有效且具有多样性的样本。问卷具有树状结构，因此不能把
所有问题当成彼此独立的固定列直接随机生成：父问题选择 `No` 后，未显示的子问题必须
记为 `N/A`。

## 策略

正式输入由 `generate_samples.py` 离线生成：

| 组别 | 比例 | 布尔题选择 Yes 的概率 | 用途 |
|---|---:|---:|---|
| `no_biased` | 30% | 15% | 覆盖低风险附近的扰动路径 |
| `yes_biased` | 20% | 85% | 覆盖高风险附近的扰动路径 |
| `balanced_random` | 50% | 50% | 扩大组合覆盖范围 |

此外单独保留 `all_no` 和 `all_yes` 两个锚点，用于回归测试和人工交叉验证。它们不应
重复运行数百次来凑样本数量。

小规模示例采样包见 `examples/sampling_preview/`，说明文档见
`docs/sampling_examples.md`。

## 去重

每条样本仅按“实际可见问题及答案”生成 canonical JSON，再计算 SHA-256：

```text
canonical_hash = SHA256(sorted(visible_question_id -> answer))
```

隐藏的 `N/A` 节点不参与哈希。若生成器无法得到 1000 个唯一可达路径，会在
`manifest.json` 中给出警告；此时应补全地图或重新设计实验，不要保留重复行。

## 原始数据建议

2 号批量执行后，原始数据至少保存：

| 字段 | 说明 |
|---|---|
| `sample_id` | 样本标识 |
| `strategy` | 采样组别 |
| `canonical_hash` | 可见路径去重哈希 |
| `resolved_answers` | 完整树状答案，隐藏题为 `N/A` |
| `summary.raw_text` | Summary 页原始文本 |
| `summary.ratings` | 各地区评级解析结果 |
| `summary.content_descriptors` | 内容描述符 |
| `summary.interactive_elements` | 交互元素 |
| `collected_at` | 采集时间 |
| `status` | 成功、验证码、限速或结构变化 |

保留全部地区评级。不要在采集阶段提前只选择某一个地区标签。

## 采集执行边界

1 号只负责一次填写脚本和输入策略。批量执行、断点续传、重试、限速控制和
`raw_data.csv` 由 2 号实现。任何重试都必须保守处理：遇到验证码后停止人工检查，
遇到限速后等待并减少频率，不加入规避平台限制的手段。
