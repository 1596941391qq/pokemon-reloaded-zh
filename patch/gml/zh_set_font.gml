if (!variable_global_exists("zh_ready")) zh_init();
draw_set_font(argument0);
global.zh_font = argument0;
zh_metrics();
