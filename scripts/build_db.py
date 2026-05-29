from __future__ import annotations

import sqlite3
from pathlib import Path
import pandas as pd

# Local config for canonical file locations
try:
    from scripts.config import FILES, DATA_PROCESSED, ROOT
except ModuleNotFoundError:  # allow running as a module or script
    from config import FILES, DATA_PROCESSED, ROOT

DB_PATH = ROOT / "data" / "ai_talks.sqlite"

TABLE_MAP = {
    "content": {
        "path": FILES["content"],
        "table": "content",
        # Map the YouTube-export column names to our snake_case schema.
        # The raw export does not include a `likes` field for this channel.
        "rename": {
            "Content": "video_id",
            "Video title": "title",
            "Views from playlist": "views",
            "Duration": "avg_view_duration",
        },
        "dtypes": {
            "video_id": "string",
            "title": "string",
            "views": "Int64",
            "likes": "Int64",
            "avg_view_duration": "float",
        },
    },
    "traffic": {
        "path": FILES["traffic"],
        "table": "traffic",
        "rename": {
            "Traffic source": "traffic_source",
            "Views": "views",
        },
        "dtypes": {
            "traffic_source": "string",
            "views": "Int64",
        },
    },
    "geography": {
        "path": FILES["geography"],
        "table": "geography",
        "rename": {
            "Geography": "country",
            "Views": "views",
        },
        "dtypes": {
            "country": "string",
            "views": "Int64",
        },
    },
    "subscriptions": {
        "path": FILES["subscriptions"],
        "table": "subscriptions",
        "rename": {
            "Subscription status": "audience_type",
            "Views": "views",
        },
        "dtypes": {
            "audience_type": "string",
            "views": "Int64",
        },
    },
    "dates": {
        "path": FILES["dates"],
        "table": "dates",
        # The daily export carries total views per day, not subscriber gains,
        # so we expose `views` rather than the original `subs_gained` slot.
        "rename": {
            "date": "date",
            "Views": "views",
        },
        "dtypes": {
            "date": "datetime64[ns]",
            "views": "Int64",
        },
    },
}


def _read_csv_safe(path: Path) -> pd.DataFrame:
    if not Path(path).exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _coerce_types(df: pd.DataFrame, dtypes: dict) -> pd.DataFrame:
    if df.empty:
        return df
    for col, dtype in dtypes.items():
        if col not in df.columns:
            # create missing columns as NA
            df[col] = pd.NA if dtype in ("Int64", "string") else None
        if dtype == "Int64":
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
        elif dtype == "float":
            df[col] = pd.to_numeric(df[col], errors="coerce")
        elif dtype == "datetime64[ns]":
            df[col] = pd.to_datetime(df[col], errors="coerce")
        elif dtype == "string":
            df[col] = df[col].astype("string")
    return df


def build_sqlite(db_path: Path = DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    try:
        for key, meta in TABLE_MAP.items():
            df = _read_csv_safe(meta["path"])  # type: ignore[arg-type]
            rename = meta.get("rename") or {}
            if not df.empty and rename:
                # If a target column already exists with a different name in the source,
                # drop the placeholder so the rename can claim it (e.g. extract_from_youtube
                # adds a `traffic_source` label column that collides with our `Traffic source`
                # rename target).
                collisions = [
                    target for source, target in rename.items()
                    if source != target and source in df.columns and target in df.columns
                ]
                if collisions:
                    df = df.drop(columns=collisions)
                df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
            df = _coerce_types(df, meta["dtypes"])  # type: ignore[arg-type]
            # reorder columns to stable schema
            cols = list(meta["dtypes"].keys())
            df = df[[c for c in cols if c in df.columns]]
            df.to_sql(meta["table"], con, if_exists="replace", index=False)
        # basic indices for performance
        try:
            con.execute("CREATE INDEX IF NOT EXISTS idx_content_video ON content(video_id)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_traffic_source ON traffic(traffic_source)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_geo_country ON geography(country)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_dates_date ON dates(date)")
        except sqlite3.DatabaseError:
            pass
    finally:
        con.close()


if __name__ == "__main__":
    build_sqlite()
    print(f"Built SQLite database at: {DB_PATH}")
