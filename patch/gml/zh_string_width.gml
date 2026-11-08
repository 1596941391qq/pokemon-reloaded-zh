// 替换 string_width：中文模式下按多行最大宽度计算
var s, w, m, p;
if (!is_string(argument0)) return string_width(argument0);
if (!variable_global_exists("zh_ready")) zh_init();
s = argument0;
if (!zh_has_high(s)) return string_width(s);
w = 0;
p = string_pos("#", s);
while (p > 0)
{
    m = zh_line_width(string_copy(s, 1, p - 1)); if (m > w) w = m;
    s = string_copy(s, p + 1, string_length(s) - p);
    p = string_pos("#", s);
}
m = zh_line_width(s); if (m > w) w = m;
return w;
