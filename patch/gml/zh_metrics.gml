// 按当前字体的行高选择 12px 或 10px 汉字图集
global.zh_lh = string_height("M");
if (global.zh_lh >= 13)
{
    global.zh_bg = zh_atlas12; global.zh_cw = 12; global.zh_ch = 16; global.zh_cols = {{COLS12}};
}
else
{
    global.zh_bg = zh_atlas10; global.zh_cw = 10; global.zh_ch = 14; global.zh_cols = {{COLS10}};
}
global.zh_dy = floor((global.zh_lh - global.zh_ch) / 2);
