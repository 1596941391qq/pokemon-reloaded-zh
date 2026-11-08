// 画一段非汉字文本，返回画完后的 x
// argument: x, y, str, c1, c2, c3, c4, alpha, mode(0=draw_text 1=draw_text_color)
if (argument8) draw_text_color(argument0, argument1, argument2, argument3, argument4, argument5, argument6, argument7);
else draw_text(argument0, argument1, argument2);
return argument0 + string_width(argument2);
