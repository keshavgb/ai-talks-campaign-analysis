-- Analysis queries for AI Talks campaign insights (SQLite dialect)

-- 1) Top-performing videos by views
SELECT
  COALESCE(video_id, '') AS video_id,
  COALESCE(title, '') AS title,
  CAST(views AS INTEGER) AS views
FROM content
ORDER BY CAST(views AS INTEGER) DESC
LIMIT 10;

-- 2) Traffic sources by total views
SELECT
  COALESCE(traffic_source, 'Unknown') AS traffic_source,
  SUM(CAST(views AS INTEGER)) AS total_views
FROM traffic
GROUP BY traffic_source
ORDER BY total_views DESC;

-- 3) Top countries by views
SELECT
  COALESCE(country, 'Unknown') AS country,
  SUM(CAST(views AS INTEGER)) AS total_views
FROM geography
GROUP BY country
ORDER BY total_views DESC
LIMIT 10;

-- 4) Subscribers gained over time (daily)
SELECT
  date,
  SUM(CAST(subs_gained AS REAL)) AS subs_gained
FROM dates
GROUP BY date
ORDER BY date ASC;

-- 5) Optional: view share from subscribed vs non-subscribed if present
-- This expects subscriptions(audience_type, views)
SELECT
  audience_type,
  SUM(CAST(views AS INTEGER)) AS views
FROM subscriptions
GROUP BY audience_type
ORDER BY views DESC;
