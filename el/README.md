# el/ — 台股資金流 Pipeline：EL 層

獨立於 `backend/` 的專案。核心抓取邏輯只依賴 `requests`，落地層可切換
DuckDB（本機開發）或 Snowflake（正式），日後搬進 Snowpark stored
procedure 時 `core/sources.py` 不需要改任何一行。

## 結構

```
el/
  core/
    contracts.py         每個來源的 RAW 表名 + 必要欄位（輕量驗證用）
    normalize.py         日期格式轉換（請求參數用西元、回應解析用民國年）
    sources.py           七個來源的抓取函式（純函式，只回傳 list[dict]）
    loader.py            DuckDB 落地：RAW schema、冪等寫入
    loader_snowflake.py  Snowflake 落地：VARIANT、key-pair 認證
  runners/
    run_local.py         CLI 入口，本機／GitHub Actions 共用
  sql/
    01_raw_tables.sql    Snowflake RAW 七張表 DDL
    02_service_user.sql  服務帳號 + key-pair + 最小權限角色
  data/
    el.duckdb            執行後產生（已在根目錄 .gitignore 排除）
```

**設計邊界**：EL 只做 E 和 L，不做 T。型別轉換、業務邏輯全部留給 dbt
staging。唯一例外是 `_trade_date`——冪等刪除要用它當鍵，必須在 EL 階段
就解析出來。

## 已實作的來源（7/8）

| RAW 表 | 支援指定日期 | 備註 |
|---|---|---|
| `src_twse_quote` | ✅ | 上市行情 |
| `src_tpex_quote` | ✅ | 上櫃行情，自帶發行股數 |
| `src_twse_inst` | ✅ | 上市三大法人（單位為股數非金額） |
| `src_tpex_inst` | ✅ | 上櫃三大法人 |
| `src_twse_exright` | ✅（區間） | 上市除權息 |
| `src_tpex_exright` | ❌ 只有今天 | 上櫃除權息，來源無日期參數 |
| `src_twse_profile` | ❌ 只有當下快照 | 上市發行股數，每月更新即可 |

後兩個是「快照型」來源，不管 `--date` 傳什麼，`_trade_date` 一律標記為
執行當天——不能誤植成使用者要求的日期，否則 RAW 表會說謊。

**尚未實作**：`src_ic_industry`（產業價值鏈分類）。這是 HTML 爬蟲而非
JSON API，需處理 ic.tpex.org.tw 不完整的憑證鏈與 Cloudflare 挑戰，且是
季更新而非日更新——技術性質與其餘七個來源不同，留待下一輪獨立實作。

## 執行

```bash
cd el
uv sync
uv run python -m runners.run_local --date 2026-09-17
```

不帶 `--date` 預設抓今天。`--runner` 預設 `local`，GitHub Actions
workflow 應傳 `--runner github_actions`，讓 RAW 表的 `_runner` 欄位能
分辨資料是哪條路徑寫入的。

### 落地到 Snowflake

先在 Snowsight 依序執行 `sql/01_raw_tables.sql` 與 `sql/02_service_user.sql`
（後者需先在本機產金鑰，步驟寫在檔案開頭的註解），然後：

```bash
uv sync --extra snowflake
export SNOWFLAKE_ACCOUNT=AO92359
export SNOWFLAKE_USER=SVC_EL_GITHUB
export SNOWFLAKE_PRIVATE_KEY="$(cat snowflake_key.p8)"
export SNOWFLAKE_PRIVATE_KEY_PASSPHRASE=...
uv run python -m runners.run_local --target snowflake --date 2026-09-17
```

## 檢查結果

```bash
uv run python -c "
import duckdb
conn = duckdb.connect('data/el.duckdb')
for t in ['src_twse_quote','src_tpex_quote','src_twse_inst','src_tpex_inst']:
    print(t, conn.execute(f'SELECT _trade_date, _runner, count(*) FROM raw.{t} GROUP BY 1,2').fetchall())
"
```

## 已知的雷

- **TWSE RWD 端點的查詢參數要用西元 `YYYYMMDD`**，不是民國年——跟回應
  *內容* 裡的欄位值用民國年是兩回事。危險之處：`MI_INDEX` 傳錯格式不會
  報錯，而是**默默回傳「今天」的資料**。驗證時要檢查回應裡伺服器回報的
  `date` 欄位，不能只看筆數合理就放心。
- **這台開發機有 DLP 透明加密**：用 Python 直接寫檔（`pathlib.write_text`）
  會讓檔案變成密文，檔頭出現 `%TSD-Header-###%`。改用編輯器或 Claude 的
  Write 工具重寫即可恢復明文。提交前值得掃一次。
