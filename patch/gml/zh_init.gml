// 中文显示补丁：初始化字符表（图集索引）
var s, n, i;
global.zh_ready = 1;
global.zh_map = ds_map_create();
s = zh_chars();
n = string_length(s) div 2;
for (i = 0; i < n; i += 1)
{
    ds_map_add(global.zh_map, ord(string_char_at(s, i * 2 + 1)) * 256 + ord(string_char_at(s, i * 2 + 2)), i);
}
global.zh_font = -1;
global.zh_halign = fa_left;
global.zh_valign = fa_top;
zh_metrics();
