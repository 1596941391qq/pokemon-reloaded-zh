// 游戏里的选项菜单切换语言时，也把语言写进 data\text\config.ini（标题画面切语言本来就会写）。
// 读档用 config.ini 里的语言（见 zh_cfg_lang），不写的话，游戏里切的语言按 F6 读档后会被改回去。
// argument0 = lan.txt 的行号（从 0 数），和标题画面写的一样。
var f;
file_delete("data\text\config.ini");
f = file_text_open_write("data\text\config.ini");
file_text_write_real(f, argument0);
file_text_close(f);
