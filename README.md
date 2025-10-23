# AI Talks Campaign Performance Analysis

End-to-end analysis of YouTube Analytics data for the AI Talks channel, producing a SQLite database, SQL insights, Python visuals, and presentation-ready reports.

## Quick Start

1) Install dependencies (use your venv):
```
pip install -r requirements.txt
```

2) Ensure processed CSVs exist in `data/processed/`:
- `content_clean_ready.csv`
- `traffic_clean_ready.csv`
- `geography_clean_ready.csv`
- `subscriptions_clean_ready.csv`
- `date_clean_ready.csv`

If missing, populate `data/raw/` from YouTube exports and run:
```
python scripts/extract_from_youtube.py
```

3) Build the SQLite database:
```
python scripts/build_db.py
```
This creates `data/ai_talks.sqlite` with tables: `content`, `traffic`, `geography`, `subscriptions`, `dates`.

4) Run EDA to generate KPIs and figures:
```
python scripts/eda_youtube.py
```
Outputs:
- Figures in `figures/`
- KPIs in `reports/kpis.csv`

5) Generate reports:
```
python scripts/generate_reports.py
```
Outputs in `reports/`:
- `data_dictionary.csv`
- `executive_summary.pdf` (requires `reportlab`)
- `insights_presentation.pptx` (requires `python-pptx`)

6) Notebook (SQL + Python integration):
- Open and run `Notebooks/campaign_analysis.ipynb`.
- It builds the DB if needed, runs SQL queries (`SQL/analysis_queries.sql` equivalents), and plots insights.

## SQL
- `SQL/create_tables.sql` — table DDL for SQLite
- `SQL/load_data.sql` — sqlite3 CLI `.import` from `data/processed/`
- `SQL/analysis_queries.sql` — key insights queries (SQLite-compatible)

## Notes
- Plots are saved to `figures/`. If you need a `visuals/` folder, mirror `figures/` outputs there.
- Configured paths live in `scripts/config.py`.
