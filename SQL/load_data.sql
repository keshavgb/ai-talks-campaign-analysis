-- Load CSV data into SQLite tables using sqlite3 CLI dot-commands
-- Usage: sqlite3 data/ai_talks.sqlite < SQL/create_tables.sql
--        sqlite3 -cmd ".mode csv" -cmd ".headers on" data/ai_talks.sqlite < SQL/load_data.sql

.mode csv
.headers on

-- Clear existing data
DELETE FROM content;
DELETE FROM traffic;
DELETE FROM geography;
DELETE FROM subscriptions;
DELETE FROM dates;

-- Import from processed CSVs
.import data/processed/content_clean_ready.csv content
.import data/processed/traffic_clean_ready.csv traffic
.import data/processed/geography_clean_ready.csv geography
.import data/processed/subscriptions_clean_ready.csv subscriptions
.import data/processed/date_clean_ready.csv dates
