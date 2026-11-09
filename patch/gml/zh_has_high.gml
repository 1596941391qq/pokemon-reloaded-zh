// 这串字要不要按汉字画
// 中文模式：有 >=129 的字节就画。
// 其他语言：只有整串不含英文字母时才画（语言菜单里的「简体中文」、玩家起的纯中文名），
// 免得西语、英语里连着的重音字符（比如 "!!" 前面的两个倒叹号、"ca" 后面的 n 和 o 带重音）被当成汉字。
var s, i, n, c, hi, zh;
s = argument0; n = string_length(s); hi = false;
zh = true;
if (variable_global_exists("language")) zh = (global.language == "zh");
for (i = 1; i <= n; i += 1)
{
    c = ord(string_char_at(s, i));
    if (c >= 129)
    {
        if (zh) return true;
        hi = true;
    }
    else if (!zh)
    {
        if ((c >= 65 && c <= 90) || (c >= 97 && c <= 122)) return false;
    }
}
return hi;
