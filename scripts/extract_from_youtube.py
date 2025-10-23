from pathlib import Path
import pandas as pd
import os

RAW = Path("data/raw")
PROCESSED = Path("data/processed")
RAW.mkdir(parents=True, exist_ok=True)
PROCESSED.mkdir(parents=True, exist_ok=True)


def resolve_folder(patterns: list[str]) -> str:
    """
    Scans RAW and returns the first subfolder whose name starts with any of the patterns (case-insensitive).
    If none are found, raises FileNotFoundError with a helpful message.
    """
    available_dirs = [d.name for d in RAW.iterdir() if d.is_dir()]
    lower_dirs = [d.lower() for d in available_dirs]
    for pat in patterns:
        pat_lower = pat.lower()
        for dir_name, dir_lower in zip(available_dirs, lower_dirs):
            if dir_lower.startswith(pat_lower):
                return dir_name
    msg = (
        f"No folder found starting with any of {patterns} in {RAW}\n"
        f"Available folders: {available_dirs}"
    )
    raise FileNotFoundError(msg)

def load_latest_csv(folder_or_patterns) -> pd.DataFrame:
    """
    folder_or_patterns: Either a string (exact folder name) or a list of patterns (see resolve_folder).
    Returns DataFrame from latest CSV in resolved folder.
    """
    resolved_folder = None
    if isinstance(folder_or_patterns, list):
        resolved_folder = resolve_folder(folder_or_patterns)
        folder_path = RAW / resolved_folder
    else:
        folder_path = RAW / folder_or_patterns
        resolved_folder = folder_or_patterns
    csv_files = list(folder_path.glob("*.csv"))
    if not csv_files:
        available = [f.name for f in folder_path.iterdir() if f.is_file()]
        raise FileNotFoundError(
            f"No CSV files found in {folder_path} (Resolved folder: '{resolved_folder}')\n"
            f"Available files: {available}"
        )
    latest_file = max(csv_files, key=lambda f: f.stat().st_mtime)
    print(f"[INFO] Using latest file for {resolved_folder}: {latest_file.name}")
    df = pd.read_csv(latest_file)
    df["source"] = resolved_folder
    return df

if __name__ == "__main__":
    targets = [
        ("Content_Ai-talks-CA", "content_clean_ready.csv"),
        (["Traffic Source_Ai-Talks-CA", "Traffic Sources_Ai-Talks-CA"], "traffic_clean_ready.csv"),
        ("Geography_Ai-Talks-CA", "geography_clean_ready.csv"),
        (["Subscription_Ai-talks-CA", "Subscription Status_Ai-talks-CA"], "subscriptions_clean_ready.csv"),
        ("Date_Ai-talks-CA", "date_clean_ready.csv"),
    ]

    for folder_or_patterns, outfile in targets:
        try:
            df = load_latest_csv(folder_or_patterns)
            (PROCESSED / outfile).parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(PROCESSED / outfile, index=False)
            print(f"[OK] Saved {outfile}")
        except FileNotFoundError as e:
            print(f"[WARN] {e}")
        except Exception as e:
            print(f"[ERROR] Failed for {folder_or_patterns}: {e}")

    print("All available latest CSVs processed → data/processed/")


    # --- Post-clean standardization for EDA ---
# This makes the processed CSVs consistent (column names & types) regardless of upstream variations.

import os
import pandas as pd
from pathlib import Path

try:
    from scripts.config import FILES, DATA_PROCESSED
except ModuleNotFoundError:
    from config import FILES, DATA_PROCESSED

def _rename_if_exists(df: pd.DataFrame, mapping: dict):
    rename_map = {old: new for old, new in mapping.items() if old in df.columns}
    return df.rename(columns=rename_map)

def standardize_processed_schema():
    # content.csv
    p = FILES.get("content")
    if p and Path(p).exists():
        df = pd.read_csv(p)
        df = _rename_if_exists(df, {
            "view_count": "views",
            "views_total": "views",
            "title": "title",
            "video_title": "title",
            "videoId": "video_id",
            "id": "video_id",
            "like_count": "likes",
            "avg_watch_seconds": "avg_view_duration",
            "avg_view_duration_sec": "avg_view_duration",
        })
        df.to_csv(p, index=False)

    # traffic.csv
    p = FILES.get("traffic")
    if p and Path(p).exists():
        df = pd.read_csv(p)
        df = _rename_if_exists(df, {
            "source": "traffic_source",
            "traffic_source_type": "traffic_source",
            "view_count": "views",
        })
        df.to_csv(p, index=False)

    # geography.csv
    p = FILES.get("geography")
    if p and Path(p).exists():
        df = pd.read_csv(p)
        df = _rename_if_exists(df, {
            "country_name": "country",
            "country_code": "country",
            "region": "country",
            "region_name": "country",
            "location": "country",
            "geo": "country",
            "view_count": "views",
        })
        df.to_csv(p, index=False)

    # dates.csv
    p = FILES.get("dates")
    if p and Path(p).exists():
        df = pd.read_csv(p)
        df = _rename_if_exists(df, {
            "day": "date",
            "report_date": "date",
            "dt": "date",
            "timestamp": "date",
            "subscribers_gained": "subs_gained",
            "subs_added": "subs_gained",
            "subscribers_added": "subs_gained",
            "net_subscribers": "subs_gained",
            "subscribers_net": "subs_gained",
            "subs": "subs_gained",
        })
        # force types
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])  # drop totals/headers
        if "subs_gained" in df.columns:
            df["subs_gained"] = pd.to_numeric(df["subs_gained"], errors="coerce").fillna(0)
        df.to_csv(p, index=False)

    # subscriptions.csv (not used in plots yet, but keep it tidy)
    p = FILES.get("subscriptions")
    if p and Path(p).exists():
        df = pd.read_csv(p)
        df = _rename_if_exists(df, {
            "subscribers_gained": "subs_gained",
            "subs_added": "subs_gained",
            "subscribers_added": "subs_gained",
        })
        df.to_csv(p, index=False)

# Run standardization automatically unless disabled
if __name__ == "__main__":
    if os.environ.get("STANDARDIZE_AFTER_CLEAN", "1") == "1":
        standardize_processed_schema()