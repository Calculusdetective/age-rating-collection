# 探针 1a：Fear = Yes，Scary elements = Often

## 目的

在已完成 `Scary elements = Rare` 的基础上，只改变频率为 `Often`，观察评级是否进一步上升。

## 操作设置

日期：2026-06-03  
问卷抓取：`results/discover_fear_often_questionnaire.json` / `results/discover_fear_often_questionnaire.png`  
Summary 抓取：`results/discover_fear_often_summary.json` / `results/discover_fear_often_summary.png`

| question_id | 取值 |
|---|---|
| `violence.exists` | no |
| `fear.contains_disturbing_content` | yes |
| `fear.scary_elements` | yes |
| `fear.horrifying_elements` | no |
| `fear.scary_frequency` | often |
| 其他所有顶层题 | no |

## 需要截图

```text
screenshots/fear_scary_often_questionnaire.png
screenshots/fear_scary_often_summary.png
```

本轮已改用 `discover` 自动抓取，结果保存在 `results/` 中。

## 记录重点

1. Summary 顶部的 Fear 概括是否从 `Rarely` 变成 `Often` 或类似文案。
2. Australia、Taiwan、Europe、Germany、Rest of world、Russia 是否比 `Rare` 更高。
3. North America 是否仍为 `Everyone`，还是升到更高等级。
4. Content descriptors 是否变化。

## Summary 结果

| 地区 | Rating authority | Rating | Content descriptors |
|---|---|---|---|
| Australia | Australian Classification Board (ACB) | Parental Guidance | Scary Scenes |
| Brazil | Classificação Indicativa (ClassInd) | Rated 10+ | Fear |
| North America | Entertainment Software Rating Board (ESRB) | Everyone 10+ | Fantasy Violence |
| South Korea | Game Rating and Administration Committee (GRAC) | 12+ | Fear |
| Taiwan | Digital Game Self-regulation Committee (DGSC) | Parental Guidance 12 | Horror |
| Saudi Arabia | General Authority of Media Regulation (Gmedia) | 12 | - |
| Europe | Pan-European Game Information (PEGI) | PEGI 7 | Fear |
| Germany | Unterhaltungssoftware Selbstkontrolle (USK) | USK: Ages 12+ | Dark Atmosphere |
| Rest of world | IARC Generic | Rated for 7+ | Fear |
| Russia | Google Play | Rated for 7+ | Fear |

Summary 页概括为：

```text
Fear: Pictures or sounds likely to be scary (Often)
```

## 与 Rare 路径对比

从 `Rare` 改为 `Often` 后，部分地区进一步升档：

| 地区 | Rare | Often |
|---|---|---|
| Brazil | All ages | Rated 10+ |
| North America | Everyone | Everyone 10+ |
| South Korea | All ages | 12+ |
| Saudi Arabia | 7 | 12 |
| Germany | USK: Ages 6+ | USK: Ages 12+ |

Australia、Taiwan、Europe、Rest of world、Russia 的年龄档位与 `Rare` 相同，但描述符可能保持或细化为 Fear/Scary/Horror 相关。

## 完成后

`Often` 未发现新增子题。暂时不要把
`fear.contains_disturbing_content.children_explored` 改成 `true`，因为
`Horrifying elements = Yes` 仍未探索。
