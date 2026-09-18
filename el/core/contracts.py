"""每個資料來源的落地契約：RAW 表名 + 必要欄位。

只用來做「這批資料形狀有沒有明顯壞掉」的輕量檢查（例如來源網站改版、
回應變成錯誤頁），不做型別轉換或業務邏輯——那些留給 dbt staging。

欄位名稱刻意保留來源的原始中文（含少數欄位自帶的空白，載入前會被
_rows_from_rwd_table 去除首尾空白），方便對照官方文件；不要在這裡
重新命名成英文，避免和 RAW payload 實際存的 key 對不上。
"""
from __future__ import annotations

RAW_TABLE_QUOTE_TWSE = "src_twse_quote"
RAW_TABLE_QUOTE_TPEX = "src_tpex_quote"
RAW_TABLE_INST_TWSE = "src_twse_inst"
RAW_TABLE_INST_TPEX = "src_tpex_inst"
RAW_TABLE_EXRIGHT_TWSE = "src_twse_exright"
RAW_TABLE_EXRIGHT_TPEX = "src_tpex_exright"
RAW_TABLE_PROFILE_TWSE = "src_twse_profile"

ALL_TABLES = [
    RAW_TABLE_QUOTE_TWSE,
    RAW_TABLE_QUOTE_TPEX,
    RAW_TABLE_INST_TWSE,
    RAW_TABLE_INST_TPEX,
    RAW_TABLE_EXRIGHT_TWSE,
    RAW_TABLE_EXRIGHT_TPEX,
    RAW_TABLE_PROFILE_TWSE,
]

# 每個來源至少要有這些欄位，缺了代表回應格式跑掉（例如變成錯誤頁或改版）
REQUIRED_FIELDS: dict[str, list[str]] = {
    RAW_TABLE_QUOTE_TWSE: ["證券代號", "收盤價", "成交金額"],
    RAW_TABLE_QUOTE_TPEX: ["代號", "收盤", "成交金額(元)"],
    RAW_TABLE_INST_TWSE: ["證券代號", "三大法人買賣超股數"],
    RAW_TABLE_INST_TPEX: ["代號", "三大法人買賣超股數合計"],
    RAW_TABLE_EXRIGHT_TWSE: ["股票代號", "除權息參考價"],
    RAW_TABLE_EXRIGHT_TPEX: ["SecuritiesCompanyCode", "ExRightsDiviendQuote"],
    RAW_TABLE_PROFILE_TWSE: ["公司代號", "已發行普通股數或TDR原股發行股數"],
}
