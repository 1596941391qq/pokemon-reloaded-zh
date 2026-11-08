// 中文文本绘制核心
// argument: x, y, str, c1, c2, c3, c4, alpha, mode(0=draw_text 1=draw_text_color)
var x0, y0, s, nl, lh, line, p, w, lx, i, n, c, k, idx, gcol, galpha, rs, prevz;
x0 = argument0; y0 = argument1; s = argument2; lh = global.zh_lh;
nl = string_count("#", s) + 1;
if (global.zh_valign == fa_middle) y0 -= floor(nl * lh / 2);
else if (global.zh_valign == fa_bottom) y0 -= nl * lh;
if (argument8) { gcol = merge_color(argument3, argument5, 0.5); galpha = argument7; }
else { gcol = draw_get_color(); galpha = draw_get_alpha(); }
draw_set_halign(fa_left); draw_set_valign(fa_top);
repeat (nl)
{
    p = string_pos("#", s);
    if (p > 0) { line = string_copy(s, 1, p - 1); s = string_copy(s, p + 1, string_length(s) - p); }
    else { line = s; s = ""; }
    w = zh_line_width(line);
    lx = x0;
    if (global.zh_halign == fa_center) lx = x0 - floor(w / 2);
    else if (global.zh_halign == fa_right) lx = x0 - w;
    n = string_length(line); i = 1; rs = 1; prevz = false;
    while (i <= n)
    {
        c = ord(string_char_at(line, i));
        if (c >= 129)
        {
            if (i < n)
            {
                k = c * 256 + ord(string_char_at(line, i + 1));
                if (ds_map_exists(global.zh_map, k))
                {
                    if (i > rs) lx = zh_draw_run(lx, y0, string_copy(line, rs, i - rs), argument3, argument4, argument5, argument6, argument7, argument8);
                    idx = ds_map_find_value(global.zh_map, k);
                    draw_background_part_ext(global.zh_bg, (idx mod global.zh_cols) * global.zh_cw, (idx div global.zh_cols) * global.zh_ch, global.zh_cw, global.zh_ch, lx, y0 + global.zh_dy, 1, 1, gcol, galpha);
                    lx += global.zh_cw; i += 2; rs = i; prevz = true; continue;
                }
            }
            else
            {
                if (i > rs) lx = zh_draw_run(lx, y0, string_copy(line, rs, i - rs), argument3, argument4, argument5, argument6, argument7, argument8);
                i += 1; rs = i; continue;
            }
        }
        if (c == 32 && prevz && i < n)
        {
            if (ord(string_char_at(line, i + 1)) >= 129)
            {
                if (i > rs) lx = zh_draw_run(lx, y0, string_copy(line, rs, i - rs), argument3, argument4, argument5, argument6, argument7, argument8);
                i += 1; rs = i; continue;
            }
        }
        prevz = false; i += 1;
    }
    if (i > rs) lx = zh_draw_run(lx, y0, string_copy(line, rs, i - rs), argument3, argument4, argument5, argument6, argument7, argument8);
    y0 += lh;
}
draw_set_halign(global.zh_halign); draw_set_valign(global.zh_valign);
