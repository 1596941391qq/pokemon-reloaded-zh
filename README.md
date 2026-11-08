# 宝可梦重装上阵 简体中文汉化（Pokémon Reloaded 中文补丁）

西班牙作者 F3R 的同人游戏 **Pokémon Reloaded / Proyecto Reloaded**（GameMaker 8 制作）的简体中文汉化。

- **对应游戏版本：The Last Beta 1.9.2.2**（`Proyecto Reloaded The Last Beta 1.9.2.2 Full.exe`，SHA-256 `772d5d45…bf07630`）
- **译名标准：宝可梦官方简体中文**。宝可梦、招式、特性、道具、图鉴、人物都以官方译名为准（数据来自 [PokeAPI](https://pokeapi.co/) 和 [神奇宝贝百科](https://wiki.52poke.com/)）；游戏原创的宝可梦、地名、人物按官方风格自译，并在术语表里标注「自译」。
- 能直接用官方原文的地方都用了官方原文，比如招式说明、特性说明、图鉴分类、图鉴说明。图鉴说明会先找出作者原文拼用了哪几版官方图鉴，再拼接对应版本的官方中文。
- 本仓库**不含游戏本体和任何原作素材**。游戏请到作者官方博客下载：<https://pokemon-reloaded.blogspot.com/>

## 当前进度

<!-- progress -->
| 文件 | 内容 | 已译 | 总数 | 进度 | 其中直接用官方原文 |
|---|---|---:|---:|---:|---:|
| `dex_espec` | 图鉴分类 | 1238 | 1238 | 100% | 1144 |
| `dex_info` | 图鉴说明 | 1238 | 1238 | 100% | 718 |
| `txt_abilities` | 特性名 | 314 | 314 | 100% | 311 |
| `txt_abilities_desc` | 特性说明 | 314 | 314 | 100% | 267 |
| `txt_adjective` | 个性描述 | 205 | 205 | 100% | 0 |
| `txt_attack` | 招式名 | 866 | 866 | 100% | 851 |
| `txt_attack_desc` | 招式说明 | 846 | 846 | 100% | 755 |
| `txt_battle` | 对战文本 | 374 | 374 | 100% | 0 |
| `txt_cartel` | 告示牌 | 458 | 458 | 100% | 0 |
| `txt_character` | 人物与称号 | 1111 | 1111 | 100% | 88 |
| `txt_creditos` | 制作人员 | 43 | 43 | 100% | 0 |
| `txt_map` | 地图名 | 186 | 186 | 100% | 0 |
| `txt_medals` | 徽章与成就 | 119 | 119 | 100% | 0 |
| `txt_menu` | 菜单与系统提示 | 2663 | 2663 | 100% | 26 |
| `txt_obj` | 道具名 | 821 | 821 | 100% | 620 |
| `txt_obj_desc` | 道具说明 | 1760 | 1760 | 100% | 0 |
| `txt_obj_secret_base` | 秘密基地物品 | 1087 | 1087 | 100% | 0 |
| `txt_pkmn` | 宝可梦名 | 1557 | 1557 | 100% | 1026 |
| `txt_places` | 地名 | 283 | 283 | 100% | 0 |
| `txt_quests` | 任务 | 1119 | 1119 | 100% | 0 |
| `txt_dialog` | 剧情对话 | 2000 | 14995 | 13% | 1 |
| `txt_exam` | 考试题 | 0 | 669 | 0% | 0 |
| `txt_keyboard` | 输入键盘 | 0 | 118 | 0% | 0 |
| **合计** | | **18602** | **32384** | **57%** | |
<!-- /progress -->

没翻到的文本会自动显示英文原文，不影响游玩。剧情对话（共约 1.5 万条）先翻了开头部分，其余会陆续补上。

## 安装方法（Windows）

1. **下载游戏**：在作者博客下载 *The Last Beta 1.9.2.2 Full* 并解压，比如解压到 `D:\Games\Proyecto Reloaded`。
2. **下载补丁**：本页右上角 **Code → Download ZIP**，解压到任意位置。
3. **装 Python**（没装过的话）：<https://www.python.org/downloads/> 下载 Python 3，安装时勾选 **Add python.exe to PATH**。
4. **打补丁**：双击补丁文件夹里的 **`安装中文补丁.bat`**，把游戏文件夹拖进窗口，按回车。大约 10 秒完成。
   - 命令行也可以：`python patch.py "D:\Games\Proyecto Reloaded"`
5. **开始游戏**：直接运行游戏 exe，默认就是简体中文。也可以在游戏的语言选项里切回英语或西语。

补丁会把原版 exe、`lan.txt`、`config.ini` 备份到游戏目录下的 **`原版备份`** 文件夹。之后每次打补丁都以这份备份为底重新生成，所以译文更新后再运行一次即可，不会越改越乱。

**恢复原版**：把 `原版备份` 里的三个文件拷回原处（exe 放回游戏根目录，另外两个放回 `data\text\`），再删掉 `data\text\zh` 文件夹。

## 已知问题

- 画在图片里的文字（标题画面、部分按钮）还是原文。
- 图鉴和道具箱的按名称排序、搜索仍按英文名。
- 中文字体用的是 12px / 10px 像素字体，个别小字号的地方可能比原文略挤。

## 术语表（可搜索）

GitHub 可以直接打开下面的表格，并用页面上的搜索框查找：

- [`glossary/glossary.csv`](glossary/glossary.csv)：宝可梦、招式、特性、道具，列出中英西三语和来源（官方/规则/自译）
- [`glossary/places.tsv`](glossary/places.tsv)：地名（星辰地区的城镇按星座和星宿译，比如 Spica = 角宿市、Sirius = 天狼市）
- [`glossary/人物.csv`](glossary/人物.csv)：人物和训练家称号（官方角色已对照神奇宝贝百科核对过）
- [`docs/对照.md`](docs/对照.md)：汉化前后对照示例

## 参与翻译

译文在 `translations/<文件>.json` 里，每条形如 `{"id": 行号, "en": 英文, "es": 西语, "zh": 中文}`，只改 `zh` 一栏。规范见 [`translations/STYLE.md`](translations/STYLE.md)。改完运行：

```
python tools/check_part.py translations/txt_dialog.json txt_dialog   # 检查控制符、编码
python tools/term_check.py                                         # 检查官方译名是否一致
```

## 原理（给想改代码的人）

- 游戏文本在 `data/text/<语言>/*.dll`，其实是纯文本，每个字节用一张固定的替换表加了密（游戏脚本 `ValuesAdjustment6`）。`tools/rtext.py` 负责解密和加密。
- GameMaker 8 自带的字体只有 256 个字符，显示不了中文。所以补丁会改游戏 exe：先按 GM8.0 的格式解密数据块，再把所有画字函数（`draw_text`、`string_width` 等）换成自己写的 `zh_*` 版本（见 `patch/gml/`），最后塞进两张中文像素字图集，并按原算法重新加密。这部分代码在 `tools/gm8_repack.py` 和 `tools/make_patch.py`。
- 中文按 GBK 存储。汉字之间插了空格，好让游戏原有的按空格断行逻辑继续工作；这种空格在两个汉字之间不占宽度。

## 致谢与许可

- 原作：F3R 与 Pokémon Reloaded 团队。宝可梦相关名称与形象的版权属于任天堂、GAME FREAK、Creatures。本项目为非商业同人汉化。
- 中文字体：[Fusion Pixel Font](https://github.com/TakWolf/fusion-pixel-font)（SIL Open Font License 1.1，见 `fonts/OFL.txt`）
- 官方译名数据：[PokeAPI](https://github.com/PokeAPI/pokeapi)、[神奇宝贝百科](https://wiki.52poke.com/)
- GM8 文件格式参考了 [OpenGMK](https://github.com/OpenGMK/OpenGMK)，本仓库的代码是重新编写的。
- 本仓库自写部分：代码 MIT；译文 CC BY-NC-SA 4.0。
