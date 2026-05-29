"""Editorial chart theme + small helpers for the AI Talks campaign report.

The goal is publication-quality figures that read like a marketing-analytics
brief: a single dominant accent color, a takeaway-style title, a quiet
subtitle, light grid, no chart frame, and value labels on the bars.
"""
from __future__ import annotations

from typing import Iterable, Optional

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

# --------------------------------------------------------------------------- #
# Palette
# --------------------------------------------------------------------------- #
PALETTE = {
    "accent":     "#2563EB",  # editorial blue — the bar that tells the story
    "accent_dim": "#1E40AF",  # darker blue for hover / secondary highlight
    "context":    "#E5E7EB",  # light gray for context bars
    "context_dk": "#D1D5DB",  # slightly darker gray when context needs more weight
    "ink":        "#111827",  # primary text
    "ink_soft":   "#4B5563",  # subtitle text
    "ink_mute":   "#9CA3AF",  # source line / footnotes
    "grid":       "#F3F4F6",  # very faint horizontal grid
    "bg":         "#FFFFFF",
}


# --------------------------------------------------------------------------- #
# Theme
# --------------------------------------------------------------------------- #
def apply_theme() -> None:
    """Install editorial defaults on matplotlib's rcParams."""
    plt.rcParams.update({
        # Typography
        "font.family": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 11,
        "text.color": PALETTE["ink"],

        # Axes
        "axes.facecolor": PALETTE["bg"],
        "axes.edgecolor": PALETTE["ink_mute"],
        "axes.labelcolor": PALETTE["ink_soft"],
        "axes.labelsize": 10,
        "axes.labelweight": "regular",
        "axes.titlesize": 14,
        "axes.titleweight": "semibold",
        "axes.titlelocation": "left",
        "axes.titlepad": 14,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.spines.bottom": True,
        "axes.linewidth": 0.8,

        # Ticks
        "xtick.color": PALETTE["ink_soft"],
        "ytick.color": PALETTE["ink"],
        "xtick.labelsize": 10,
        "ytick.labelsize": 11,
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "xtick.major.pad": 6,
        "ytick.major.pad": 8,

        # Grid
        "axes.grid": True,
        "axes.grid.axis": "x",
        "grid.color": PALETTE["grid"],
        "grid.linewidth": 1.0,
        "grid.linestyle": "-",
        "axes.axisbelow": True,

        # Figure
        "figure.facecolor": PALETTE["bg"],
        "figure.dpi": 110,
        "savefig.dpi": 220,
        "savefig.facecolor": PALETTE["bg"],
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.35,

        # Legend
        "legend.frameon": False,
        "legend.fontsize": 10,
    })


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def thousands(x: float, _pos: int = 0) -> str:
    """Format a number with thousands separators, dropping trailing .0."""
    if x >= 1000:
        return f"{x:,.0f}"
    if float(x).is_integer():
        return f"{int(x)}"
    return f"{x:,.1f}"


THOUSANDS = FuncFormatter(thousands)


def style_axes(ax: Axes, *, x_grid: bool = True) -> None:
    """Apply per-axes polish that rcParams can't fully express."""
    ax.spines["bottom"].set_color(PALETTE["context_dk"])
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", length=0)
    if x_grid:
        ax.grid(axis="x", color=PALETTE["grid"], linewidth=1.0)
        ax.grid(axis="y", visible=False)
    ax.set_axisbelow(True)


def add_titles(
    fig: Figure,
    title: str,
    subtitle: Optional[str] = None,
    *,
    x: float = 0.02,
    y_title: float = 0.965,
    y_subtitle: float = 0.915,
) -> None:
    """Add an editorial-style title (takeaway) and quieter subtitle above the axes."""
    fig.text(
        x, y_title, title,
        fontsize=18, fontweight="bold", color=PALETTE["ink"],
        ha="left", va="top",
    )
    if subtitle:
        fig.text(
            x, y_subtitle, subtitle,
            fontsize=11, color=PALETTE["ink_soft"],
            ha="left", va="top",
        )


def add_source(fig: Figure, text: str, *, x: float = 0.02, y: float = 0.02) -> None:
    """Small footer line, bottom-left."""
    fig.text(
        x, y, text,
        fontsize=9, color=PALETTE["ink_mute"],
        ha="left", va="bottom",
    )


def bar_colors(labels: Iterable[str], highlight: Iterable[str]) -> list[str]:
    """Return a list of colors: accent for any label in `highlight`, context otherwise."""
    highlight_set = {h.lower() for h in highlight}
    return [
        PALETTE["accent"] if str(lbl).lower() in highlight_set else PALETTE["context"]
        for lbl in labels
    ]


def annotate_bars_h(
    ax: Axes,
    values: Iterable[float],
    *,
    pad_frac: float = 0.012,
    fontsize: int = 10,
    color: Optional[str] = None,
) -> None:
    """Write value labels at the end of each horizontal bar."""
    values = list(values)
    if not values:
        return
    xmax = max(values)
    pad = xmax * pad_frac if xmax else 0
    for i, v in enumerate(values):
        ax.text(
            v + pad, i, thousands(v),
            va="center", ha="left",
            fontsize=fontsize,
            color=color or PALETTE["ink"],
            fontweight="medium",
        )


# --------------------------------------------------------------------------- #
# Back-compat shims (kept so existing callers don't break while we migrate)
# --------------------------------------------------------------------------- #
def set_wide(figsize=(14, 6), title=None, xlabel=None, ylabel=None, rotate_x=0):
    """Legacy entrypoint. Prefer building figures explicitly with apply_theme()."""
    apply_theme()
    plt.figure(figsize=figsize)
    if title:
        plt.title(title)
    if xlabel:
        plt.xlabel(xlabel)
    if ylabel:
        plt.ylabel(ylabel)
    if rotate_x:
        plt.xticks(rotation=rotate_x)


def savefig(path):
    """Save without invoking tight_layout — callers manage axes via subplots_adjust."""
    plt.savefig(path)
    plt.close()
