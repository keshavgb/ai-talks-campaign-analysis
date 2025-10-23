"""Central configuration for file locations and shared directories."""
from pathlib import Path
from typing import Dict

# Project root inferred from this file's location (…/scripts/config.py -> project root)
ROOT = Path(__file__).resolve().parents[1]

DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
FIGURES_DIR = ROOT / "figures"
REPORTS_DIR = ROOT / "reports"

# Ensure downstream scripts never fail because folders are missing
for _path in (DATA_RAW, DATA_PROCESSED, FIGURES_DIR, REPORTS_DIR):
    _path.mkdir(parents=True, exist_ok=True)

# Canonical processed filenames used throughout the pipeline
FILES: Dict[str, Path] = {
    "content": DATA_PROCESSED / "content_clean_ready.csv",
    "traffic": DATA_PROCESSED / "traffic_clean_ready.csv",
    "geography": DATA_PROCESSED / "geography_clean_ready.csv",
    "subscriptions": DATA_PROCESSED / "subscriptions_clean_ready.csv",
    "dates": DATA_PROCESSED / "date_clean_ready.csv",
}
