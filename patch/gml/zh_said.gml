// 按「说话」键打的字里有没有这句口令（召唤雷吉家族、对战前说「不使用道具」、叫泳圈鼬「橙橙果」）。
// 原版是 string_pos(口令, string_lower(打的字))。中文口令在文本里汉字之间插了断行空格，
// 玩家照着告示牌打的字永远对不上（11-15 粉丝问召唤雷吉要打中文还是英文），所以两边去掉空格再比。
// 英文口令也认：繁体系统打不出简体字的玩家可以打英文。
// argument0 = 打的字，argument1 = 当前语言的口令，argument2 = 英文口令（小写）
var t, k;
t = string_lower(argument0);
if (string_pos(argument1, t) != 0) return true;
if (argument2 != "" && string_pos(argument2, t) != 0) return true;
k = string_replace_all(argument1, " ", "");
if (k == "") return false;
return string_pos(k, string_replace_all(argument0, " ", "")) != 0;
