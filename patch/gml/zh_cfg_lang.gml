// 读档时用的语言：取标题画面选的语言（data\text\config.ini 里是 lan.txt 的行号）。
// 读档有两条路：标题画面读档，和游戏里按 F6 / 菜单读档。后者会重启游戏、跳过标题画面，
// 语言停在游戏默认的西语，所以不能只靠标题画面设好的 global.language。
// argument0 = 存档里记的语言，读不到设置时退回用它（和原版一样）。
var f, n, i, l;
l = argument0;
if (!file_exists("data\text\config.ini") || !file_exists("data\text\lan.txt")) return l;
f = file_text_open_read("data\text\config.ini");
n = file_text_read_real(f);
file_text_close(f);
f = file_text_open_read("data\text\lan.txt");
for (i = 0; i < n && !file_text_eof(f); i += 1) file_text_readln(f);
if (!file_text_eof(f)) l = string_copy(file_text_read_string(f), 0, 2);
file_text_close(f);
return l;
