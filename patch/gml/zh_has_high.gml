// 字符串里有没有 >=129 的字节（可能是汉字）
var s, i, n;
s = argument0; n = string_length(s);
for (i = 1; i <= n; i += 1)
{
    if (ord(string_char_at(s, i)) >= 129) return true;
}
return false;
