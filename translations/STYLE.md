# 翻译规范

目标：把 Pokémon Reloaded（宝可梦重装上阵）的文本翻成**宝可梦官方简体中文风格**。

## 必须遵守

1. **专有名词查表，不要自己发明**
   - 宝可梦、招式、特性、道具：`glossary/glossary.csv`（官方译名，来源列写“官方/规则/自译”）
   - 地名：`glossary/places.tsv`；道路 `Route 5` = `5号道路`；地区 `Star Region / Región Star` = `星辰地区`
   - 人物：`translations/txt_character.json`（有了以后以它为准）
   - 表里没有的官方内容，用宝可梦官方简中（参照神奇宝贝百科 52poke），比如 Gym=道馆、Gym Leader=道馆馆主、Trainer=训练家、Elite Four=四天王、Champion=冠军、Badge=徽章、Poké Ball=精灵球、PC=电脑、Bag=包包、Pokédex=宝可梦图鉴、HP、PP 保留、Team Rocket=火箭队、Professor Oak=大木博士、Ash=小智、Brock=小刚、Misty=小霞。
   - 能力：攻击、防御、特攻、特防、速度、命中率、闪避率；属性：一般、火、水、草、电、冰、格斗、毒、地面、飞行、超能力、虫、岩石、幽灵、龙、恶、钢、妖精。
   - 状态：睡眠、中毒、剧毒、灼伤、冰冻、麻痹、混乱、着迷。
2. **控制符原样保留，位置对应**
   - `#` 换行，`@` 翻页，`$par1$`、`$par2$`、`$prota$`、`$rival$` 等变量占位（`$...$` 一律不动）。
   - `(&Z)`、`(&X)` 这类按键标记原样保留。
   - 不要新增或删掉 `#`、`@`。英文里没有的换行不要加（游戏会自动断行）。
3. **标点用全角中文标点**：，。！？……“”‘’（）：；。省略号用“……”。英文按键名、数字、`$par1$` 两侧不加空格也行，和中文之间不需要空格。
4. **汉字只用常用字**（GB2312 范围），避免生僻字和繁体字。
5. 玩家称“你”。口吻自然、简洁，像官方游戏文本，不要翻译腔。人物性格从原文语气判断。
6. 英文是从西班牙语翻过去的，常有错误；**英文和西语不一致时以西语为准**（`es` 字段）。
7. 只填 `zh`，不要改 `en`/`es`。原文为空或只是符号的行，`zh` 照抄原文。

## 交付格式

在 `work/parts/` 下写一个 JSON 文件（文件名任务里会给），内容是数组：

```json
[{"id": 12, "zh": "要更改画面缩放模式吗？##－当前模式－#$par1$"}, ...]
```

写完运行校验，必须零错误：

```
python3 -I tools/check_part.py work/parts/<你的文件>.json <源文件名，如 txt_menu>
```

## 常见官方译名补充（表里查不到时用）

- 组织：火箭队、海洋队（Team Aqua，不是“水舰队”）、熔岩队、银河队、等离子队、闪焰队、骷髅队、以太基金会
- 设施/玩法：华丽大赛（Contest）、宝可梦全能竞技赛（Pokéathlon）、对战开拓区（Battle Frontier）、培育屋（Day Care）、宝可梦中心、友好商店（Poké Mart）、宝可梦联盟、道馆
- 道具常用：超级环（Mega Ring）、超级手镯（Mega Bracelet）、Ｚ纯晶、银色王冠/金色王冠、奈克洛索尔合体器/奈克洛露奈合体器
- 人物：一律以 `translations/txt_character.json` 为准（已对照神奇宝贝百科核对过官方角色）。**注意：这个游戏的英文栏常常直接用西语名**（如 Lem=希特隆、Corelia=可尔妮、Dianta=卡露妮、Mento=一树），按英文和西语两栏都去人物表里找。官方角色举例：琴音（Lyra）、阿响（Ethan/Gold）、满充（Wally）、阿驯（Barry）、黑连（Cheren）、白露（Bianca）、山梨博士（Rowan）、布拉塔诺博士（Sycamore）、帅哥（Looker）。

- 其他地区补充（52poke 核对）：映雪市（Snowbelle City）、精炼之塔（Tower of Mastery）、究极之洞（Ultra Wormhole）、辉克拉尼天文台（Hokulani Observatory）、莫恩（Mohn）、成也·大木（Samson Oak）、惩戒之壶（Prison Bottle）

## 剧情里反复出现的自译名（已定，照用）

| 原文（英 / 西） | 译名 |
|---|---|
| Team Rekiem | 安魂队（Rekiem Castle = 安魂城堡） |
| Elite Squad / Escuadrón Élite | 精英小队 |
| Vital Particle / Partícula Vital | 活力粒子 |
| Star Frontier / Frente Star | 星之开拓区（各区：锦标赛开拓区、工厂开拓区……） |
| Star Pokémon League / Liga Pokémon Star | 星辰宝可梦联盟 |
| Scorpio Building / Rascacielos Scorpio | 天蝎大厦 |
| Combat Faculty / Facultad de Combate | 对战学院 |
| Rigel Saloon | 参宿酒馆 |
| Star Region Bank | 星辰银行 |
| Great Wise Elder / Gran Sabio Anciano | 大贤者 |
| Day Care | 培育屋 |
| Discount Coupon | 折价券 |
| Distortion World | 毁坏的世界 |
| Galar / Hisui / Kalos / Paldea | 伽勒尔 / 洗翠 / 卡洛斯 / 帕底亚 |
| Professor Oak 全名 Samuel Oak | 大木雪成 |
| Frontier Symbol / Símbolo | 纹章（银纹章、金纹章） |
| Battle Points / PB | 对战点数（BP） |
| Battle Dome / Cúpula de Batalla | 对战巨蛋 |
| Front Line Café / Cafetería Primera Línea | 前线咖啡馆 |
| Aspirant / Aspirante，Sub Ace / Ace | 挑战者，副王牌 / 王牌 |
| Mortal Particle / Partícula Mortal | 死亡粒子 |
| Z-Ring / Pulsera Z，Mega Stone | Ｚ手环，超级石 |
| Terra Sanctuary / Santuario Terra | 地球圣域 |
| Great Stellar Island / Gran Isla Estelar | 星辰大岛 |
| Achievement Building | 成就大楼 |
| Pokémon University | 宝可梦大学 |
| Name Rater / Move Reminder / Move Tutor | 姓名鉴定师 / 招式回忆师 / 招式教学师 |
| Swords of Justice | 圣剑士（官方） |
| Battle Potentials / Potenciales de Batalla | 战斗潜力者 |
| € | 元（GBK 没有欧元符号，金额后写“元”） |

**徽章**：其他地区的徽章名已对照神奇宝贝百科核对，见 `glossary/徽章.csv`（如 Knuckle Badge=拳击徽章、Balance Badge=天秤徽章、Feather Badge=白羽徽章），一律查表。

**地名特别注意**：其他地区（关都、城都、丰缘、神奥、合众、卡洛斯）的城镇名已经收进 `glossary/places.tsv`，一律查表。之前凭记忆写错过好几次（华蓝市/满金市/浅葱市、秋叶镇/茵郁市、琉璃市/绿岭市）。表里查不到的官方地名，宁可写成通用说法（如“城都的那座港口城市”），也不要凭记忆编。翻之前可以先在 `translations/txt_dialog.json` 里搜已有译文，沿用前面的译法。
