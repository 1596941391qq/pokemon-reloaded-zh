// 单行（不含 #）的像素宽度：ASCII 段用原字体量，汉字按图集宽度算；两个汉字之间的空格不占宽度
var s, n, i, c, w, rs, prevz;
s = argument0; n = string_length(s); w = 0; i = 1; rs = 1; prevz = false;
while (i <= n)
{
    c = ord(string_char_at(s, i));
    if (c >= 129)
    {
        if (i < n)
        {
            if (ds_map_exists(global.zh_map, c * 256 + ord(string_char_at(s, i + 1))))
            {
                if (i > rs) w += string_width(string_copy(s, rs, i - rs));
                w += global.zh_cw; i += 2; rs = i; prevz = true; continue;
            }
        }
        else
        {
            if (i > rs) w += string_width(string_copy(s, rs, i - rs));
            i += 1; rs = i; continue;
        }
    }
    if (c == 32 && prevz && i < n)
    {
        if (ord(string_char_at(s, i + 1)) >= 129)
        {
            if (i > rs) w += string_width(string_copy(s, rs, i - rs));
            i += 1; rs = i; continue;
        }
    }
    prevz = false; i += 1;
}
if (i > rs) w += string_width(string_copy(s, rs, i - rs));
return w;
