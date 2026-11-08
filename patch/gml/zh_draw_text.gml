// 替换 draw_text
if (!is_string(argument2)) { draw_text(argument0, argument1, argument2); exit; }
if (!variable_global_exists("zh_ready")) zh_init();
if (!zh_has_high(argument2)) { draw_text(argument0, argument1, argument2); exit; }
zh_draw_core(argument0, argument1, argument2, 0, 0, 0, 0, 1, 0);
