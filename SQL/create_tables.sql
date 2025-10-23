-- Create tables for AI Talks campaign analysis in SQLite
-- Target DB: data/ai_talks.sqlite

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS content (
  video_id TEXT,
  title TEXT,
  views INTEGER,
  likes INTEGER,
  avg_view_duration REAL
);

CREATE TABLE IF NOT EXISTS traffic (
  traffic_source TEXT,
  views INTEGER
);

CREATE TABLE IF NOT EXISTS geography (
  country TEXT,
  views INTEGER
);

CREATE TABLE IF NOT EXISTS subscriptions (
  audience_type TEXT,
  views INTEGER
);

CREATE TABLE IF NOT EXISTS dates (
  date TEXT,
  subs_gained REAL
);
