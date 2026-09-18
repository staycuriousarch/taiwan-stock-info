-- ===========================================================================
-- RAW 層：EL 的落地目標。七張表結構完全一致，只有 payload 內容不同。
-- 在 Snowsight worksheet 執行一次即可。
--
-- 與本機 DuckDB 版（el/core/loader.py）唯一的差異是 payload 型別：
-- DuckDB 沒有 VARIANT，用 VARCHAR 存 JSON 字串；Snowflake 用真正的
-- VARIANT，dbt staging 才能直接 payload:欄位名::型別 取值。
--
-- 刻意不加 CLUSTER BY：每日約 2 萬列、一年不到 500 萬列，Snowflake 的
-- micro-partition 本來就處理得很好。在這種資料量上開叢集鍵只會招來
-- automatic clustering 的額外費用，換不到查詢效益。
-- ===========================================================================

CREATE DATABASE IF NOT EXISTS TW_STOCK;
CREATE SCHEMA   IF NOT EXISTS TW_STOCK.RAW;

USE SCHEMA TW_STOCK.RAW;

-- 第一張表定義完整結構，其餘六張用 LIKE 複製同一套欄位
CREATE TABLE IF NOT EXISTS SRC_TWSE_QUOTE (
    _load_id    VARCHAR       COMMENT '一次執行一個 UUID',
    _loaded_at  TIMESTAMP_NTZ COMMENT 'UTC，dbt source freshness 用',
    _source_url VARCHAR       COMMENT '出問題時能重現當初那次呼叫',
    _runner     VARCHAR       COMMENT 'local | github_actions | snowpark',
    _trade_date DATE          COMMENT '冪等刪除與分區用',
    payload     VARIANT       COMMENT '一列原始記錄，原封不動'
)
COMMENT = '上市個股每日收盤行情（TWSE MI_INDEX）';

CREATE TABLE IF NOT EXISTS SRC_TPEX_QUOTE   LIKE SRC_TWSE_QUOTE;
CREATE TABLE IF NOT EXISTS SRC_TWSE_INST    LIKE SRC_TWSE_QUOTE;
CREATE TABLE IF NOT EXISTS SRC_TPEX_INST    LIKE SRC_TWSE_QUOTE;
CREATE TABLE IF NOT EXISTS SRC_TWSE_EXRIGHT LIKE SRC_TWSE_QUOTE;
CREATE TABLE IF NOT EXISTS SRC_TPEX_EXRIGHT LIKE SRC_TWSE_QUOTE;
CREATE TABLE IF NOT EXISTS SRC_TWSE_PROFILE LIKE SRC_TWSE_QUOTE;

COMMENT ON TABLE SRC_TPEX_QUOTE   IS '上櫃個股每日收盤行情（TPEX afterTrading/otc，自帶發行股數）';
COMMENT ON TABLE SRC_TWSE_INST    IS '上市三大法人買賣超（TWSE T86，單位為股數非金額）';
COMMENT ON TABLE SRC_TPEX_INST    IS '上櫃三大法人買賣超（TPEX insti/dailyTrade）';
COMMENT ON TABLE SRC_TWSE_EXRIGHT IS '上市除權息計算結果（TWSE TWT49U，支援區間查詢）';
COMMENT ON TABLE SRC_TPEX_EXRIGHT IS '上櫃除權息計算結果（TPEX openapi，僅當日、無日期參數）';
COMMENT ON TABLE SRC_TWSE_PROFILE IS '上市公司基本資料（TWSE t187ap03_L，含已發行普通股數）';

SHOW TABLES IN SCHEMA TW_STOCK.RAW;
