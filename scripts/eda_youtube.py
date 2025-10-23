"""Exploratory data analysis for the AI Talks YouTube campaign."""
from __future__ import annotations

import os
import re
import warnings
from pathlib import Path
from typing import Dict, Iterable, Mapping, Optional

import pandas as pd

# Ensure Matplotlib has a writable cache folder even in sandboxed environments
_MPL_CACHE = Path(__file__).resolve().parents[1] / ".matplotlib_cache"
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_CACHE))
_MPL_CACHE.mkdir(parents=True, exist_ok=True)

import matplotlib

matplotlib.use("Agg")  # headless backend suitable for CLI/CI usage
import matplotlib.pyplot as plt

try:
    import seaborn as sns

    HAVE_SEABORN = True
except ModuleNotFoundError:  # seaborn is optional
    sns = None  # type: ignore
    HAVE_SEABORN = False
    print("[EDA] seaborn not installed; falling back to Matplotlib-only plots.")

# Local project imports (support both `python -m scripts.eda_youtube` and direct execution)
try:
    from scripts.config import FILES, FIGURES_DIR, REPORTS_DIR
    from scripts.plotting_utils import savefig, set_wide
except ModuleNotFoundError:
    from config import FILES, FIGURES_DIR, REPORTS_DIR
    from plotting_utils import savefig, set_wide

RESOLVED: Dict[str, str] = {}


# --------------------------------------------------------------------------- #
# Column resolution utilities
# --------------------------------------------------------------------------- #
def _normalize(text: str) -> str:
    """Simplify strings to improve fuzzy column matching."""
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _find_col(df: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
    """Return the first matching column from candidates using lenient but safe heuristics."""
    if df.empty or not df.columns.size:
        return None

    normalized: Dict[str, str] = {}
    for col in df.columns:
        key = _normalize(col)
        if key not in normalized:
            normalized[key] = col

    for cand in candidates:
        norm = _normalize(cand)
        if norm in normalized:
            return normalized[norm]

    for cand in candidates:
        norm = _normalize(cand)
        if len(norm) < 3:
            continue
        for col_norm, original in normalized.items():
            if norm in col_norm or col_norm in norm:
                return original

    return None


# --------------------------------------------------------------------------- #
# Validation / loading
# --------------------------------------------------------------------------- #
def validate_inputs(dfs: Mapping[str, pd.DataFrame]) -> None:
    """Populate RESOLVED with the best-effort column names present in each dataframe."""
    RESOLVED.clear()
    messages = []

    # content
    content = dfs.get("content")
    if content is None:
        messages.append("missing dataframe: content")
    else:
        RESOLVED["content.views"] = _find_col(
            content,
            ("views", "view_count", "views_total", "views_sum"),
        ) or ""
        if not RESOLVED["content.views"]:
            messages.append("content missing a views column (tried: views, view_count, views_total, views_sum)")
        RESOLVED["content.title"] = _find_col(
            content,
            ("title", "video_title", "video title", "name", "videoname"),
        ) or "title"
        RESOLVED["content.video_id"] = _find_col(
            content,
            ("video_id", "video id", "content", "content_id", "id", "videoid"),
        ) or "video_id"
        RESOLVED["content.likes"] = _find_col(
            content,
            ("likes", "like_count", "likes_total"),
        ) or "likes"
        RESOLVED["content.avg_dur"] = _find_col(
            content,
            (
                "avg_view_duration",
                "average_view_duration",
                "avg_watch_seconds",
                "avg_view_duration_sec",
                "duration",
            ),
        ) or "avg_view_duration"

    # traffic
    traffic = dfs.get("traffic")
    if traffic is None:
        messages.append("missing dataframe: traffic")
    else:
        RESOLVED["traffic.source"] = _find_col(
            traffic,
            ("traffic_source", "source", "traffic_source_type"),
        ) or ""
        RESOLVED["traffic.views"] = _find_col(
            traffic,
            ("views", "view_count"),
        ) or ""
        if not RESOLVED["traffic.source"]:
            messages.append("traffic missing a source column (tried: traffic_source, source, traffic_source_type)")
        if not RESOLVED["traffic.views"]:
            messages.append("traffic missing a views column (tried: views, view_count)")

    # geography
    geography = dfs.get("geography")
    if geography is None:
        messages.append("missing dataframe: geography")
    else:
        RESOLVED["geo.country"] = _find_col(
            geography,
            (
                "country",
                "country_name",
                "country_code",
                "geo",
                "location",
                "region",
                "region_name",
                "region_code",
            ),
        ) or ""
        RESOLVED["geo.views"] = _find_col(
            geography,
            ("views", "view_count"),
        ) or ""
        if not RESOLVED["geo.country"]:
            obj_cols = [c for c in geography.columns if geography[c].dtype == "object"]
            if obj_cols:
                RESOLVED["geo.country"] = obj_cols[0]
                messages.append(
                    f"geography country not found; using first text column: {obj_cols[0]}"
                )
            else:
                messages.append(
                    "geography missing a country-like column (tried: country, country_name, country_code, geo, location, region, region_name, region_code)"
                )
        if not RESOLVED["geo.views"]:
            messages.append("geography missing a views column (tried: views, view_count)")

    # dates
    dates = dfs.get("dates")
    if dates is None:
        messages.append("missing dataframe: dates")
    else:
        RESOLVED["dates.date"] = _find_col(dates, ("date", "day", "report_date")) or ""
        RESOLVED["dates.subs"] = _find_col(
            dates,
            (
                "subs_gained",
                "subscribers_gained",
                "subs_added",
                "subscribers_added",
                "subs",
                "subscribers",
                "net_subscribers",
                "subscribers_net",
            ),
        ) or ""
        if not RESOLVED["dates.date"]:
            like_date = _find_col(dates, ("dt", "timestamp")) or ""
            if like_date:
                RESOLVED["dates.date"] = like_date
                messages.append(f"dates date not found; using: {like_date}")
            else:
                messages.append("dates missing a date column (tried: date, day, report_date)")
        if not RESOLVED["dates.subs"]:
            candidates = [
                c
                for c in dates.columns
                if ("sub" in c.lower()) and pd.api.types.is_numeric_dtype(dates[c])
            ]
            if candidates:
                RESOLVED["dates.subs"] = candidates[0]
                messages.append(
                    f"dates subscribers-gained not found; using numeric column containing 'sub': {candidates[0]}"
                )
            else:
                messages.append("dates missing a subscribers-gained column (tried multiple variants and heuristics)")

    # subscriptions
    subscriptions = dfs.get("subscriptions")
    if subscriptions is None:
        messages.append("missing dataframe: subscriptions")
    else:
        RESOLVED["subscriptions.audience"] = _find_col(
            subscriptions,
            (
                "audience_type",
                "viewer_status",
                "subscription_status",
                "subscriber_status",
                "status",
            ),
        ) or ""
        RESOLVED["subscriptions.views"] = _find_col(
            subscriptions,
            ("views", "view_count", "views_total", "views_sum"),
        ) or ""
        if not RESOLVED["subscriptions.audience"]:
            obj_cols = [c for c in subscriptions.columns if subscriptions[c].dtype == "object"]
            if obj_cols:
                RESOLVED["subscriptions.audience"] = obj_cols[0]
                messages.append(
                    f"subscriptions audience column not found; using first text column: {obj_cols[0]}"
                )
            else:
                messages.append(
                    "subscriptions missing an audience column (tried viewer_status, subscription_status, subscriber_status, status)"
                )
        if not RESOLVED["subscriptions.views"]:
            numeric_cols = [
                c for c in subscriptions.columns if pd.api.types.is_numeric_dtype(subscriptions[c])
            ]
            if numeric_cols:
                RESOLVED["subscriptions.views"] = numeric_cols[0]
                messages.append(
                    f"subscriptions views metric not found; using first numeric column: {numeric_cols[0]}"
                )
            else:
                messages.append("subscriptions missing a numeric metric column (tried views variants)")

    if messages:
        print("\n[EDA] Schema warnings (continuing with best effort):\n  - " + "\n  - ".join(messages) + "\n")


def load_data() -> Dict[str, pd.DataFrame]:
    """Read every dataframe declared in config.FILES, skipping any that are absent."""
    dfs: Dict[str, pd.DataFrame] = {}
    missing = []
    for name, path in FILES.items():
        try:
            if not path.exists():
                missing.append(f"{name}: {path}")
                continue
            dfs[name] = pd.read_csv(path)
        except FileNotFoundError:
            missing.append(f"{name}: {path}")
        except Exception as exc:
            raise RuntimeError(f"Failed reading {name} from {path}: {exc}") from exc

    if missing:
        print("\n[EDA] Skipping missing datasets (this is OK if you don't need them):\n  - " + "\n  - ".join(missing) + "\n")

    return dfs


# --------------------------------------------------------------------------- #
# KPI helpers and plotting
# --------------------------------------------------------------------------- #
def kpi_table(dfs: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """Compute a light-weight set of KPIs shared with downstream reporting."""
    content = dfs.get("content", pd.DataFrame())
    dates = dfs.get("dates", pd.DataFrame())
    subscriptions = dfs.get("subscriptions", pd.DataFrame())

    vcol = RESOLVED.get("content.views", "views")
    idcol = RESOLVED.get("content.video_id", "video_id")
    likes_col = RESOLVED.get("content.likes", "likes")
    dur_col = RESOLVED.get("content.avg_dur", "avg_view_duration")
    subs_col = RESOLVED.get("dates.subs", "subs_gained")
    subs_audience = RESOLVED.get("subscriptions.audience")
    subs_metric = RESOLVED.get("subscriptions.views", "views")

    total_videos = content[idcol].nunique() if idcol in content else (len(content) if not content.empty else 0)
    total_views = content[vcol].sum() if vcol in content else 0
    total_likes = content[likes_col].sum() if likes_col in content else 0
    avg_view_duration = content[dur_col].mean() if dur_col in content else None
    subs_total_gain = dates[subs_col].sum() if subs_col in dates else 0

    subscribed_view_share = None
    if (
        not subscriptions.empty
        and subs_audience
        and subs_audience in subscriptions.columns
        and subs_metric in subscriptions.columns
    ):
        grouped = subscriptions.groupby(subs_audience)[subs_metric].sum(min_count=1)
        total_metric = grouped.sum()
        if total_metric:
            subscribed_metric = grouped[[idx for idx in grouped.index if "sub" in str(idx).lower()]].sum()
            subscribed_view_share = subscribed_metric / total_metric if total_metric else None

    return pd.DataFrame(
        {
            "total_videos": [total_videos],
            "total_views": [total_views],
            "total_likes": [total_likes],
            "avg_view_duration_sec": [avg_view_duration],
            "subs_total_gain": [subs_total_gain],
            "subscribed_view_share": [subscribed_view_share],
        }
    )


def plot_top_videos(content: pd.DataFrame, top_n: int = 10) -> None:
    """Create a horizontal bar chart summarising the top performing videos."""
    vcol = RESOLVED.get("content.views", "views")
    tcol = RESOLVED.get("content.title", "title")
    if content.empty or vcol not in content.columns:
        return

    df = content.sort_values(vcol, ascending=False).head(top_n).copy()
    label_col = tcol if tcol in df.columns else "_label"
    if label_col not in df.columns:
        df[label_col] = df.index.astype(str)

    set_wide(title=f"Top {top_n} Videos by Views", xlabel="Views", ylabel="Video", rotate_x=0)
    if HAVE_SEABORN and sns is not None:
        sns.barplot(data=df, x=vcol, y=label_col)
    else:
        plt.barh(df[label_col], df[vcol])
        plt.gca().invert_yaxis()
    savefig(FIGURES_DIR / "top_videos_by_views.png")


def plot_traffic_sources(traffic: pd.DataFrame) -> None:
    """Summarise traffic sources by total views."""
    src = RESOLVED.get("traffic.source", "traffic_source")
    vcol = RESOLVED.get("traffic.views", "views")
    if traffic.empty or src not in traffic.columns or vcol not in traffic.columns:
        return

    grp = traffic.groupby(src, as_index=False)[vcol].sum().sort_values(vcol, ascending=False)
    set_wide(title="Traffic Sources by Views", xlabel="Views", ylabel="Source")
    if HAVE_SEABORN and sns is not None:
        sns.barplot(data=grp, x=vcol, y=src)
    else:
        plt.barh(grp[src].astype(str), grp[vcol])
        plt.gca().invert_yaxis()
    savefig(FIGURES_DIR / "traffic_sources.png")


def plot_top_countries(geography: pd.DataFrame, top_n: int = 10) -> None:
    """Visualise the top countries by view volume."""
    ccol = RESOLVED.get("geo.country", "")
    vcol = RESOLVED.get("geo.views", "")
    if (
        geography.empty
        or not ccol
        or not vcol
        or ccol not in geography.columns
        or vcol not in geography.columns
    ):
        return

    grp = (
        geography.groupby(ccol, as_index=False)[vcol]
        .sum()
        .sort_values(vcol, ascending=False)
        .head(top_n)
    )
    set_wide(title=f"Top {top_n} Countries by Views", xlabel="Views", ylabel="Country")
    if HAVE_SEABORN and sns is not None:
        sns.barplot(data=grp, x=vcol, y=ccol)
    else:
        plt.barh(grp[ccol].astype(str), grp[vcol])
        plt.gca().invert_yaxis()
    savefig(FIGURES_DIR / "top_countries.png")


def plot_subs_over_time(dates: pd.DataFrame) -> None:
    """Plot subscriber gains over time as a line chart."""
    dcol = RESOLVED.get("dates.date", "date")
    scol = RESOLVED.get("dates.subs", "subs_gained")
    if dates.empty or dcol not in dates.columns or scol not in dates.columns:
        return

    tmp = dates[[dcol, scol]].dropna().sort_values(dcol)
    set_wide(title="Subscribers Gained Over Time", xlabel="Date", ylabel="Subs Gained")
    if HAVE_SEABORN and sns is not None:
        sns.lineplot(data=tmp, x=dcol, y=scol)
    else:
        plt.plot(tmp[dcol], tmp[scol])
    savefig(FIGURES_DIR / "subs_over_time.png")


def plot_subscriber_breakdown(subscriptions: pd.DataFrame) -> None:
    """Visualise the relative performance of subscriber segments."""
    audience_col = RESOLVED.get("subscriptions.audience")
    metric_col = RESOLVED.get("subscriptions.views", "views")
    if (
        subscriptions.empty
        or not audience_col
        or audience_col not in subscriptions.columns
        or metric_col not in subscriptions.columns
    ):
        return

    grp = (
        subscriptions.groupby(audience_col, as_index=False)[metric_col]
        .sum(min_count=1)
        .sort_values(metric_col, ascending=False)
    )
    set_wide(title="Subscribed vs Non-Subscribed Audience", xlabel="Views", ylabel="Audience Type")
    if HAVE_SEABORN and sns is not None:
        sns.barplot(data=grp, x=metric_col, y=audience_col)
    else:
        plt.barh(grp[audience_col].astype(str), grp[metric_col])
        plt.gca().invert_yaxis()
    savefig(FIGURES_DIR / "subscriber_breakdown.png")


# --------------------------------------------------------------------------- #
# Tabular exports
# --------------------------------------------------------------------------- #
def export_group_summary(df: pd.DataFrame, group_col: str, value_col: str, output_name: str) -> None:
    """Write grouped summaries to the reports directory for downstream reporting."""
    if df.empty or group_col not in df.columns or value_col not in df.columns:
        return
    summary = (
        df.groupby(group_col, as_index=False)[value_col]
        .sum(min_count=1)
        .sort_values(value_col, ascending=False)
    )
    summary.to_csv(REPORTS_DIR / output_name, index=False)


# --------------------------------------------------------------------------- #
# Main entrypoint
# --------------------------------------------------------------------------- #
def main() -> None:
    """Run the entire EDA workflow: load data, validate schemas, and produce outputs."""
    dfs = load_data()
    validate_inputs(dfs)

    print("[EDA] Resolved columns:")
    for key in sorted(RESOLVED):
        if RESOLVED[key]:
            print(f"  - {key} -> {RESOLVED[key]}")

    if "dates" in dfs:
        dcol = RESOLVED.get("dates.date")
        if dcol and dcol in dfs["dates"].columns:
            series = dfs["dates"][dcol]
            if pd.api.types.is_datetime64_any_dtype(series):
                parsed = series
            else:
                parsed = pd.to_datetime(series, errors="coerce", format="ISO8601")
                if parsed.notna().sum() == 0 and series.dropna().size:
                    with warnings.catch_warnings():
                        warnings.filterwarnings(
                            "ignore",
                            message="Could not infer format",
                            category=UserWarning,
                        )
                        parsed = pd.to_datetime(series, errors="coerce")
            bad = parsed.isna().sum()
            if bad:
                print(f"[EDA] Dropping {bad} non-date rows from 'dates'.")
            dfs["dates"][dcol] = parsed
            dfs["dates"] = dfs["dates"].dropna(subset=[dcol])
            scol = RESOLVED.get("dates.subs")
            if scol and scol in dfs["dates"].columns:
                dfs["dates"][scol] = pd.to_numeric(dfs["dates"][scol], errors="coerce").fillna(0)

    kpis = kpi_table(dfs)
    kpis.to_csv(REPORTS_DIR / "kpis.csv", index=False)

    if "content" in dfs:
        plot_top_videos(dfs["content"])
    if "traffic" in dfs:
        plot_traffic_sources(dfs["traffic"])
    if "geography" in dfs:
        plot_top_countries(dfs["geography"])
    if "dates" in dfs:
        plot_subs_over_time(dfs["dates"])
    if "subscriptions" in dfs:
        plot_subscriber_breakdown(dfs["subscriptions"])
        subs_audience = RESOLVED.get("subscriptions.audience")
        subs_metric = RESOLVED.get("subscriptions.views", "views")
        if subs_audience and subs_metric:
            export_group_summary(
                dfs["subscriptions"],
                subs_audience,
                subs_metric,
                "subscriber_breakdown.csv",
            )

    print("EDA complete. Figures saved in /figures and KPIs in /reports/kpis.csv")


if __name__ == "__main__":
    main()
