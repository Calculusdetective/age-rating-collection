# 全 No 基线记录

## 基线输入

日期：2026-06-03  
截图：

- `screenshots/问卷全no.png`
- `screenshots/全no对应评级.png`

类别：`Game`

所有当前可见问题均选择 `No`。在该路径下，截图中未出现任何子问题。

## 当前可见顶层问题

| question_id | 章节 | 全 No 取值 |
|---|---|---|
| `violence.exists` | Violence, Blood, or Gory Images | no |
| `fear.contains_disturbing_content` | Fear | no |
| `sexuality.exists` | Sexuality, Suggestiveness, or Dating Games | no |
| `gambling.exists` | Gambling Themes, Simulated Gambling, or Real Gambling | no |
| `language.offensive_language` | Language | no |
| `controlled_substance.exists` | Controlled Substance | no |
| `crude_humor.exists` | Crude Humor | no |
| `digital_purchases.exists` | Digital Purchases, Cash Convertible Rewards, or NFTs | no |
| `misc.user_interaction` | Miscellaneous | no |
| `misc.precise_location` | Miscellaneous | no |
| `misc.germany_nazi_symbols` | Miscellaneous | no |
| `misc.korea_national_identity` | Miscellaneous | no |
| `misc.terrorism_advocacy` | Miscellaneous | no |
| `misc.realistic_crimes` | Miscellaneous | no |

## 全 No Summary 结果

| 地区 | Rating authority | Rating | Content descriptors |
|---|---|---|---|
| Australia | Australian Classification Board (ACB) | General | General |
| Brazil | Classificação Indicativa (ClassInd) | All ages | - |
| North America | Entertainment Software Rating Board (ESRB) | Everyone | - |
| South Korea | Game Rating and Administration Committee (GRAC) | All ages | - |
| Taiwan | Digital Game Self-regulation Committee (DGSC) | General Public | - |
| Saudi Arabia | General Authority of Media Regulation (Gmedia) | 3 | - |
| Europe | Pan-European Game Information (PEGI) | PEGI 3 | - |
| Germany | Unterhaltungssoftware Selbstkontrolle (USK) | USK: All ages | - |
| Rest of world | IARC Generic | Rated for 3+ | - |
| Russia | Google Play | Rated for 3+ | - |

## 结论

全 No 是最低风险锚点，后续用于校验脚本是否能稳定复现 Summary。它不提供任何子树信息。
下一步应一次只把一个顶层问题改为 `Yes`，观察新增子问题和 Summary 变化。
