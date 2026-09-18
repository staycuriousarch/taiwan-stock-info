-- ===========================================================================
-- GitHub Actions 用的服務帳號：key-pair 認證，不用密碼。
--
-- 為什麼不用密碼：服務帳號不該用密碼，而且 Snowflake 對密碼登入的 MFA
-- 要求越來越嚴，CI 環境沒辦法做 MFA。key-pair 是 Snowflake 對程式化存取
-- 的建議做法，也順帶回應了 Trust Center 那條資安建議的實質精神——雖然
-- 我們刻意不設 network policy（GitHub runner IP 是動態的，設了會斷線）。
--
-- 執行順序：先在本機產金鑰（見下方註解），再回來跑這支 SQL。
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- 步驟 A：在本機產生金鑰對（在終端機執行，不是在這裡）
--
--   # 產生私鑰（加密，會要求輸入 passphrase）
--   openssl genrsa 2048 | openssl pkcs8 -topk8 -v2 aes-256-cbc -inform PEM -out snowflake_key.p8
--
--   # 從私鑰導出公鑰
--   openssl rsa -in snowflake_key.p8 -pubout -out snowflake_key.pub
--
--   # 顯示公鑰內容，貼到下面步驟 C 的 RSA_PUBLIC_KEY
--   cat snowflake_key.pub
--
-- snowflake_key.p8（私鑰）絕對不要進版控，它要貼進 GitHub Secrets。
-- ---------------------------------------------------------------------------

USE ROLE ACCOUNTADMIN;

-- 步驟 B：專用角色與權限（最小權限：只能寫 RAW，不能碰其他 schema）
CREATE ROLE IF NOT EXISTS EL_LOADER
  COMMENT = 'GitHub Actions EL 專用：只能寫入 TW_STOCK.RAW';

GRANT USAGE ON DATABASE TW_STOCK           TO ROLE EL_LOADER;
GRANT USAGE ON SCHEMA   TW_STOCK.RAW       TO ROLE EL_LOADER;
GRANT SELECT, INSERT, DELETE
  ON ALL TABLES IN SCHEMA TW_STOCK.RAW     TO ROLE EL_LOADER;
-- 之後新增的表也自動涵蓋（例如加上 ic 產業鏈那張）
GRANT SELECT, INSERT, DELETE
  ON FUTURE TABLES IN SCHEMA TW_STOCK.RAW  TO ROLE EL_LOADER;

-- 給一顆小 warehouse，並確保會自動休眠（省 credit）
CREATE WAREHOUSE IF NOT EXISTS EL_WH
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND   = 60
  AUTO_RESUME    = TRUE
  INITIALLY_SUSPENDED = TRUE
  COMMENT = 'EL 載入專用，XS + 60 秒自動休眠';

GRANT USAGE ON WAREHOUSE EL_WH TO ROLE EL_LOADER;

-- 步驟 C：建立服務使用者，把公鑰貼進去
-- ↓↓↓ 把 cat snowflake_key.pub 的內容（去掉頭尾的 -----BEGIN/END----- 兩行，
--     並把中間所有行接成一整串、不要換行）貼在這裡 ↓↓↓
CREATE USER IF NOT EXISTS SVC_EL_GITHUB
  TYPE = SERVICE                    -- 服務帳號類型，不適用 MFA、不能用密碼登入
  DEFAULT_ROLE      = EL_LOADER
  DEFAULT_WAREHOUSE = EL_WH
  RSA_PUBLIC_KEY    = 'PASTE_YOUR_PUBLIC_KEY_HERE'
  COMMENT = 'GitHub Actions 每日 EL 排程用';

GRANT ROLE EL_LOADER TO USER SVC_EL_GITHUB;

-- 步驟 D：確認設定
DESC USER SVC_EL_GITHUB;
SHOW GRANTS TO ROLE EL_LOADER;
