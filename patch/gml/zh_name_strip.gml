// 起名检查用：去掉汉字（GBK 双字节），只留单字节字符。
// 原版 NameValidator 按字节查西语标点和 @ \ 等禁用字符，汉字的第二个字节会被误判。
var s, i, n, c, r;
s = argument0; n = string_length(s); r = "";
i = 1;
while (i <= n)
{
    c = ord(string_char_at(s, i));
    if (c >= 129) { i += 2; continue; }
    r += string_char_at(s, i);
    i += 1;
}
return r;
