# 探针 1：仅 Fear = Yes

## 目的

验证 `Fear` 顶层题改为 `Yes` 后的真实子树，并记录“Scary elements + Rare”路径如何影响 Summary。

## 操作设置

日期：2026-06-03  
问卷截图：`screenshots/仅fear_yes.png`  
Summary 截图：`screenshots/fear_yes评级.png`

| question_id | 取值 |
|---|---|
| `violence.exists` | no |
| `fear.contains_disturbing_content` | yes |
| `fear.scary_elements` | yes |
| `fear.horrifying_elements` | no |
| `fear.scary_frequency` | rare |
| `sexuality.exists` | no |
| `gambling.exists` | no |
| `language.offensive_language` | no |
| `controlled_substance.exists` | no |
| `crude_humor.exists` | no |
| `digital_purchases.exists` | no |
| `misc.user_interaction` | no |
| `misc.precise_location` | no |
| `misc.germany_nazi_symbols` | no |
| `misc.korea_national_identity` | no |
| `misc.terrorism_advocacy` | no |
| `misc.realistic_crimes` | no |

Summary 页将该路径概括为：

```text
Fear: Pictures or sounds likely to be scary (Rarely)
```

## 子问题记录

| question_id | 问题原文 | 选项 | 父条件 | 本轮取值 |
|---|---|---|---|---|
| `fear.scary_elements` | Scary elements | checked / unchecked | `fear.contains_disturbing_content = yes` | checked |
| `fear.horrifying_elements` | Horrifying elements | checked / unchecked | `fear.contains_disturbing_content = yes` | unchecked |
| `fear.scary_frequency` | How frequent are the scary elements? | Rare / Often | `fear.scary_elements = yes` | Rare |

## Summary 结果

| 地区 | Rating authority | Rating | Content descriptors |
|---|---|---|---|
| Australia | Australian Classification Board (ACB) | Parental Guidance | Scary Scenes |
| Brazil | Classificação Indicativa (ClassInd) | All ages | - |
| North America | Entertainment Software Rating Board (ESRB) | Everyone | Mild Fantasy Violence |
| South Korea | Game Rating and Administration Committee (GRAC) | All ages | Fear |
| Taiwan | Digital Game Self-regulation Committee (DGSC) | Parental Guidance 12 | Horror |
| Saudi Arabia | General Authority of Media Regulation (Gmedia) | 7 | - |
| Europe | Pan-European Game Information (PEGI) | PEGI 7 | Fear |
| Germany | Unterhaltungssoftware Selbstkontrolle (USK) | USK: Ages 6+ | Scary Moments |
| Rest of world | IARC Generic | Rated for 7+ | Fear |
| Russia | Google Play | Rated for 7+ | Fear |

## 与全 No 基线对比

`Scary elements = yes` 且频率为 `Rare` 后，多个地区评级上升：

- Australia: `General` -> `Parental Guidance`
- Taiwan: `General Public` -> `Parental Guidance 12`
- Saudi Arabia: `3` -> `7`
- Europe: `PEGI 3` -> `PEGI 7`
- Germany: `USK: All ages` -> `USK: Ages 6+`
- Rest of world / Russia: `Rated for 3+` -> `Rated for 7+`

Brazil、North America、South Korea 的年龄档位未升高，但 Content descriptors 出现了 Fear 相关描述。

## 异常记录

| 项目 | 结果 |
|---|---|
| reCAPTCHA 是否出现 | 截图中未见 |
| 是否限速 | 截图中未见 |
| 页面是否需要重新登录 | 未记录 |
| 是否点击最终 Submit | 否 |

## 尚未探索

- `fear.scary_frequency = often`
- `fear.horrifying_elements = yes`
- `fear.scary_elements = no` 且 `fear.horrifying_elements = yes`

因此 `fear.contains_disturbing_content.children_explored` 仍保持 `false`，正式采样继续暂停。
