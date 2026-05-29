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
    from scripts.plotting_utils import (
        PALETTE, THOUSANDS, add_source, add_titles, annotate_bars_h,
        apply_theme, bar_colors, savefig, set_wide, style_axes,
    )
except ModuleNotFoundError:
    from config import FILES, FIGURES_DIR, REPORTS_DIR
    from plotting_utils import (
        PALETTE, THOUSANDS, add_source, add_titles, annotate_bars_h,
        apply_theme, bar_colors, savefig, set_wide, style_axes,
    )

# Shared editorial caption used on every chart
SOURCE_LINE = "Source: YouTube Analytics  ·  AI Talks campaign  ·  Feb–Sep 2025"

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


# ISO-2 → friendly country name for the small set we currently surface.
_COUNTRY_NAMES = {
    "US": "United States", "IN": "India", "ET": "Ethiopia",
    "GB": "United Kingdom", "CA": "Canada", "AU": "Australia",
    "DE": "Germany", "FR": "France", "BR": "Brazil", "MX": "Mexico",
    "NG": "Nigeria", "PK": "Pakistan", "ID": "Indonesia", "PH": "Philippines",
    "JP": "Japan", "KR": "South Korea", "ES": "Spain", "IT": "Italy",
    "NL": "Netherlands", "RU": "Russia", "ZA": "South Africa", "EG": "Egypt",
    "KE": "Kenya", "GH": "Ghana", "TR": "Turkey", "SA": "Saudi Arabia",
    "AE": "United Arab Emirates", "SG": "Singapore", "MY": "Malaysia",
}


def _normalize_ai(text: str) -> str:
    """Replace standalone 'Ai' with 'AI' (matches the conventional acronym casing)."""
    return re.sub(r"\bAi\b", "AI", text)


def _short_episode(title: str) -> str:
    """Strip the 'AI Talks | Episode N:' prefix when present so headlines stay punchy."""
    short = title.split(":", 1)[1].strip() if ":" in title else title
    return _normalize_ai(short)


def plot_top_videos(content: pd.DataFrame, top_n: int = 10) -> None:
    """Top episodes by playlist-sourced views, ranked horizontal bars."""
    vcol = RESOLVED.get("content.views", "views")
    tcol = RESOLVED.get("content.title", "title")
    if content.empty or vcol not in content.columns or tcol not in content.columns:
        return

    grp = (
        content.groupby(tcol, as_index=False)[vcol]
        .sum(min_count=1)
        .dropna(subset=[vcol])
        .sort_values(vcol, ascending=False)
        .head(top_n)
        .sort_values(vcol, ascending=True)  # ascending so largest sits at top in barh
    )
    if grp.empty:
        return

    labels = [_normalize_ai(str(t)) for t in grp[tcol].tolist()]
    values = grp[vcol].tolist()
    leader = grp.iloc[-1][tcol]

    apply_theme()
    height = max(4.5, 0.55 * len(grp) + 3.0)
    fig, ax = plt.subplots(figsize=(14, height))
    fig.subplots_adjust(top=0.78, left=0.32, right=0.95, bottom=0.16)

    ax.barh(
        labels, values,
        color=bar_colors(labels, highlight={leader}),
        height=0.72, edgecolor="none",
    )
    style_axes(ax)
    ax.xaxis.set_major_formatter(THOUSANDS)
    ax.set_xlim(0, max(values) * 1.18)
    ax.set_xlabel("Playlist-sourced views", labelpad=10)
    ax.set_ylabel("")
    annotate_bars_h(ax, values)

    add_titles(
        fig,
        title=f"{_short_episode(leader)} leads playlist-sourced views",
        subtitle="Top episodes by views originating from YouTube playlists",
    )
    add_source(fig, SOURCE_LINE)
    savefig(FIGURES_DIR / "top_videos_by_views.png")


def plot_traffic_sources(traffic: pd.DataFrame) -> None:
    """Views by traffic source — External highlighted as the largest contributor."""
    src = RESOLVED.get("traffic.source", "traffic_source")
    vcol = RESOLVED.get("traffic.views", "views")
    if traffic.empty or src not in traffic.columns or vcol not in traffic.columns:
        return

    grp = (
        traffic.groupby(src, as_index=False)[vcol]
        .sum()
        .sort_values(vcol, ascending=True)
    )
    labels = grp[src].astype(str).tolist()
    values = grp[vcol].tolist()
    total = float(sum(values)) or 1.0
    leader = grp.iloc[-1][src]
    leader_share = grp.iloc[-1][vcol] / total

    apply_theme()
    fig, ax = plt.subplots(figsize=(14, 7.5))
    fig.subplots_adjust(top=0.78, left=0.22, right=0.95, bottom=0.12)

    ax.barh(
        labels, values,
        color=bar_colors(labels, highlight={str(leader)}),
        height=0.72, edgecolor="none",
    )
    style_axes(ax)
    ax.xaxis.set_major_formatter(THOUSANDS)
    ax.set_xlim(0, max(values) * 1.12)
    ax.set_xlabel("Views", labelpad=10)
    ax.set_ylabel("")
    annotate_bars_h(ax, values)

    add_titles(
        fig,
        title=f"{leader} traffic drives {leader_share*100:.0f}% of AI Talks views",
        subtitle="Views by YouTube traffic source",
    )
    add_source(fig, SOURCE_LINE)
    savefig(FIGURES_DIR / "traffic_sources.png")


def plot_top_countries(geography: pd.DataFrame, top_n: int = 10) -> None:
    """Views by viewer country, with ISO codes mapped to readable names."""
    ccol = RESOLVED.get("geo.country", "")
    vcol = RESOLVED.get("geo.views", "")
    if (
        geography.empty or not ccol or not vcol
        or ccol not in geography.columns or vcol not in geography.columns
    ):
        return

    grp = (
        geography.groupby(ccol, as_index=False)[vcol]
        .sum()
        .sort_values(vcol, ascending=False)
        .head(top_n)
    )
    if grp.empty:
        return

    grp[ccol] = grp[ccol].astype(str).map(lambda c: _COUNTRY_NAMES.get(c.upper(), c))
    grp = grp.sort_values(vcol, ascending=True)
    labels = grp[ccol].tolist()
    values = grp[vcol].tolist()
    total = float(sum(values)) or 1.0
    leader = grp.iloc[-1][ccol]
    leader_share = grp.iloc[-1][vcol] / total

    apply_theme()
    height = max(3.5, 0.7 * len(grp) + 2.8)
    fig, ax = plt.subplots(figsize=(14, height))
    fig.subplots_adjust(top=0.74, left=0.22, right=0.95, bottom=0.18)

    ax.barh(
        labels, values,
        color=bar_colors(labels, highlight={leader}),
        height=0.6, edgecolor="none",
    )
    style_axes(ax)
    ax.xaxis.set_major_formatter(THOUSANDS)
    ax.set_xlim(0, max(values) * 1.18)
    ax.set_xlabel("Views", labelpad=10)
    ax.set_ylabel("")
    annotate_bars_h(ax, values)

    add_titles(
        fig,
        title=f"{leader} accounts for {leader_share*100:.0f}% of attributable views",
        subtitle=f"Views by viewer country  ·  top {len(grp)} of {len(grp)} reported",
    )
    add_source(fig, SOURCE_LINE)
    savefig(FIGURES_DIR / "top_countries.png")


def plot_views_over_time(dates: pd.DataFrame) -> None:
    """Daily views across the campaign with a 7-day moving average overlaid."""
    dcol = RESOLVED.get("dates.date", "date")
    if dates.empty or dcol not in dates.columns or "Views" not in dates.columns:
        return

    tmp = dates[[dcol, "Views"]].dropna().sort_values(dcol).copy()
    if tmp.empty:
        return
    tmp["rolling"] = tmp["Views"].rolling(7, min_periods=1).mean()

    peak_idx = tmp["Views"].idxmax()
    peak_day = tmp.loc[peak_idx, dcol]
    peak_val = float(tmp.loc[peak_idx, "Views"])

    apply_theme()
    fig, ax = plt.subplots(figsize=(14, 5.8))
    fig.subplots_adjust(top=0.78, left=0.08, right=0.95, bottom=0.16)

    ax.bar(
        tmp[dcol], tmp["Views"],
        color=PALETTE["context_dk"], width=1.0,
        label="Daily views", edgecolor="none",
    )
    ax.plot(
        tmp[dcol], tmp["rolling"],
        color=PALETTE["accent"], linewidth=2.4,
        label="7-day moving average",
    )

    # Reverse the grid orientation for a time series
    style_axes(ax, x_grid=False)
    ax.grid(axis="y", color=PALETTE["grid"], linewidth=1.0)
    ax.yaxis.set_major_formatter(THOUSANDS)

    from matplotlib.dates import DateFormatter, MonthLocator
    ax.xaxis.set_major_locator(MonthLocator())
    ax.xaxis.set_major_formatter(DateFormatter("%b %Y"))

    ax.set_xlabel("")
    ax.set_ylabel("Views", labelpad=10)
    leg = ax.legend(loc="upper right", frameon=False, fontsize=10)
    for txt in leg.get_texts():
        txt.set_color(PALETTE["ink_soft"])

    add_titles(
        fig,
        title=f"Daily views peaked at {int(peak_val):,} on {peak_day:%b %d, %Y}",
        subtitle="Total daily views with 7-day moving average",
    )
    add_source(fig, SOURCE_LINE)
    savefig(FIGURES_DIR / "views_over_time.png")


def plot_subscriber_breakdown(subscriptions: pd.DataFrame) -> None:
    """100%-stacked single bar showing subscriber vs non-subscriber view share."""
    audience_col = RESOLVED.get("subscriptions.audience")
    metric_col = RESOLVED.get("subscriptions.views", "views")
    if (
        subscriptions.empty or not audience_col
        or audience_col not in subscriptions.columns
        or metric_col not in subscriptions.columns
    ):
        return

    grp = subscriptions.groupby(audience_col)[metric_col].sum(min_count=1)
    if grp.empty:
        return

    sub_keys = [k for k in grp.index if "sub" in str(k).lower() and "not" not in str(k).lower()]
    sub = float(grp[sub_keys].sum()) if sub_keys else 0.0
    not_sub = float(grp.sum() - sub)
    total = sub + not_sub
    if total <= 0:
        return
    sub_share = sub / total

    apply_theme()
    fig, ax = plt.subplots(figsize=(14, 3.0))
    fig.subplots_adjust(top=0.55, left=0.05, right=0.95, bottom=0.30)

    bar_height = 0.55
    ax.barh([0], [sub], color=PALETTE["accent"], height=bar_height, edgecolor="none")
    ax.barh([0], [not_sub], left=[sub], color=PALETTE["context_dk"], height=bar_height, edgecolor="none")

    # Inline labels — accent segment in white, gray segment in ink
    ax.text(
        sub / 2, 0,
        f"Subscribed  ·  {sub_share*100:.0f}%   ({int(sub):,} views)",
        va="center", ha="center", color="white", fontsize=12, fontweight="semibold",
    )
    ax.text(
        sub + not_sub / 2, 0,
        f"Not subscribed  ·  {(1-sub_share)*100:.0f}%   ({int(not_sub):,} views)",
        va="center", ha="center", color=PALETTE["ink"], fontsize=12, fontweight="semibold",
    )

    ax.set_xlim(0, total)
    ax.set_ylim(-0.6, 0.6)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.grid(False)

    add_titles(
        fig,
        title=f"Subscribers contribute {sub_share*100:.0f}% of views — non-subs drive {(1-sub_share)*100:.0f}%",
        subtitle="View share by audience type",
        y_title=0.90, y_subtitle=0.74,
    )
    add_source(fig, SOURCE_LINE)
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
        plot_views_over_time(dfs["dates"])
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
