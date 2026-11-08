// 替换 draw_text_color
if (!is_string(argument2)) { draw_text_color(argument0, argument1, argument2, argument3, argument4, argument5, argument6, argument7); exit; }
if (!variable_global_exists("zh_ready")) zh_init();
if (!zh_has_high(argument2)) { draw_text_color(argument0, argument1, argument2, argument3, argument4, argument5, argument6, argument7); exit; }
zh_draw_core(argument0, argument1, argument2, argument3, argument4, argument5, argument6, argument7, 1);
