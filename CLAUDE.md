# 專案脈絡

台股資訊網站。兩個階段，兩條互不干擾的資料管線。

| 階段 | 目標 | 目錄 | 資料源 |
|---|---|---|---|
| 一 | 個股查詢（四面向摘要 + K 線） | `backend/` `frontend/` | FinMind |
| 二 | 全市場熱力圖 + 產業資金流泡泡圖 | `el/`（未來加 `dbt/`） | 證交所／櫃買開放資料 |

第二階段另起爐灶的原因：**FinMind 免費層（register）不支援全市場批次**。
不帶 `data_id` 的 `TaiwanStockPrice` / `PER` / `InstitutionalInvestorsBuySell`
一律回 `HTTP 400 "Your level is register"`，逐檔抓 2000 檔又會超過 600/hr
上限。所以全市場橫切面走官方開放資料，`backend/` 維持原樣不動。

## 目前進度

**可用**：`backend/` `frontend/` 皆可跑；`el/` 七個來源本機 DuckDB 落地
已實測正確（2026-09-14、09-17 兩天），冪等重跑驗證過。

**已寫好但未實測**（需先在 Snowflake 設定才能驗）：`el/sql/*.sql`、
`el/core/loader_snowflake.py`、`run_local.py --target snowflake`。

**未實作**：`src_ic_industry`（產業鏈分類爬蟲）、`.github/workflows/`、
整個 dbt 專案。

## 第二階段的已定案決策

這些討論過拍板了，不需要重新評估：

- **熱力圖方格面積 = 市值**（非成交金額）。需要發行股數，且必須取「當時」
  的版本（公司增資後股數會變，用今天的股數回推去年市值會錯）。
- **泡泡圖資金流 = 三大法人買賣超金額**。來源給的是**股數**，需 × 當日
  成交均價（成交金額 ÷ 成交股數）換算。
- **跨產業鏈個股採「完整重複計入」**，不做 1/N 分攤。約 700 檔跨多條鏈
  （例：1410 新纖同屬半導體／石化／紡織）。後果：各產業加總會超過市場
  實際總額，所以 X 軸應標示為「資金流入強度」而非宣稱絕對金額。橋接表
  保留 `weight` 欄位預設 1.0，日後要改只動一處。
- **排程 17:00**。法人買賣超 15:00–16:00 才發布，更早會抓到空資料。
- **資料量小是刻意的**——目的是用小專案熟悉 Snowflake 平台能力，不需要
  質疑「這規模值不值得用 Snowflake」。
- **服務層不直連 Snowflake**。最低計費 60 秒 + 冷啟動慢，marts 匯出
  Parquet 給 DuckDB 讀，Snowflake 停掉網站也還能運作。
- **EL 走雙軌**：GitHub Actions = 日常正式排程；Snowpark + Task = 作品
  展示。共用同一份 `el/core`。

## 設計邊界

**EL 只做 E 和 L，不做 T。** 型別轉換、業務邏輯全部留給 dbt staging。
唯一例外是 `_trade_date`——冪等刪除要用它當鍵，必須在 EL 階段解析出來。

`core/sources.py` **只能依賴 `requests`**。因為這份程式碼要能原封不動搬
進 Snowpark stored procedure，而 Snowpark 的套件來源限 Snowflake 的
Anaconda channel（`httpx` 不保證有）。Snowflake 連線相關依賴設成
optional-dependencies，不污染共用層。

## 踩過的雷

**TWSE RWD 端點的查詢參數要用西元 `YYYYMMDD`，不是民國年。** 這跟回應
*內容* 裡的欄位值用民國年是兩回事，很容易搞混。危險之處：`MI_INDEX` 傳
錯格式**不會報錯，而是默默回傳「今天」的資料**（`T86` 則會明確報錯）。
→ 驗證時必須檢查回應裡伺服器回報的 `date` 欄位，不能只看筆數合理。

**`tpex_exright` 與 `twse_profile` 沒有日期參數**，只能取得「查詢當下」
的快照。`run_local.py` 特別處理：這兩個來源不管 `--date` 傳什麼，
`_trade_date` 一律標記執行當天，不能誤植成使用者要求的日期。

**TPEX 的部分 openapi 端點會傳到一半斷線**（`peer closed connection`）：
`tpex_mainboard_daily_close_quotes`、`mopsfin_t187ap03_O` → 改用 RWD 端點。
找端點先查 `www.tpex.org.tw/openapi/swagger.json`（225 個端點總表）。

**`ic.tpex.org.tw` 憑證鏈不完整**（時好時壞的 `CERTIFICATE_VERIFY_FAILED`），
且掛 Cloudflare 挑戰。寫爬蟲時要處理。

**Snowflake connector 的 `paramstyle` 必須指定 `qmark`**，不能用預設的
`pyformat`——TWSE 欄位名本身含百分比符號（如「漲跌百分比(%)」），
`pyformat` 會把資料裡的 `%` 當佔位符而炸掉。

**公司開發機（D:\Proj_Financial_Info）有 DLP 透明加密**：用 Python 直接
寫檔（`pathlib.write_text`）會讓檔案變成密文，檔頭出現 `%TSD-Header-###%`。
→ 改專案內的檔案請用編輯工具或 bash heredoc。這是該台機器的特性，在其他
電腦上可能不適用，但提交前掃一次 `grep -r "TSD-Header" --include="*.py"`
不吃虧。

## 產業分類來源

`ic.tpex.org.tw`（產業價值鏈資訊平台）無 API，但成分股**直接內嵌在
`introduce.php?ic=XXXX` 的 HTML**，不需跑 JS。三層結構：47 條主產業鏈
→ 節點（`id="ic_link_D100"`，如 IC設計／晶圓製造／封測）→ 細分
（`sc_link_D310`，如晶圓製造 26 家）。完整鏈清單在頁面的
`<select><option value='D000'>`。共收錄 2366 檔。外國公司沒有
`company_basic.php?stk_code=` 連結，可藉此濾掉。

**限制**：該站不提供歷史成分股，snapshot 只能從開始跑的那天起累積。
回補期間的產業歸屬只能用「當前分類」近似——建議在 marts 加
`industry_as_of_is_approximate` 旗標誠實標記，不要假裝精確。

## 除權息假跌

除息當天股價自然下跌，但那不是資金流出，熱力圖會出現誤導的綠色。
正確算法是 `(收盤價 - 除權息參考價) / 除權息參考價`。
上市用 `TWT49U`（可查區間），上櫃用 `tpex_exright_daily`（**僅當日、
無日期參數，歷史無法回補**）。

## 不在版控裡的東西

換機器要另外準備：

- `backend/.env` 的 `FINMIND_TOKEN`
- Snowflake 金鑰（`snowflake_key.p8`）與環境變數，見 `el/README.md`
- Snowflake 帳號：`AO92359`，AWS `ap-northeast-2`(Seoul)，Standard edition

## 環境

- 後端／EL 用 `uv`，前端用 `npm`
- Windows 主控台印中文要設 `PYTHONUTF8=1`
- `el/` 執行：`cd el && uv run python -m runners.run_local --date YYYY-MM-DD`
