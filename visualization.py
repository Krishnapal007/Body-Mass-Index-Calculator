"""
visualization.py
----------------
Matplotlib chart builders. Figures are created with matplotlib.figure.Figure
(not pyplot) so they can be embedded safely inside Tkinter.
"""

from datetime import datetime

import matplotlib.dates as mdates
from matplotlib.figure import Figure
from matplotlib.patches import Patch

from bmi_calculator import CATEGORY_COLORS, CATEGORY_ORDER

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# (lower, upper, category) bands drawn behind the trend line
BANDS = [(0, 18.5, "Underweight"), (18.5, 25, "Normal"),
         (25, 30, "Overweight"), (30, 100, "Obese")]

LINE_COLORS = ["#4F46E5", "#0891B2", "#DB2777", "#7C3AED", "#CA8A04",
               "#059669", "#E11D48", "#2563EB"]


class GraphError(Exception):
    """Raised when a graph cannot be generated or saved."""


def create_trend_figure(records_by_user):
    """BMI line chart: date on X, BMI on Y, one line per user.

    records_by_user: {username: [record dicts, oldest first]}
    """
    data = {u: r for u, r in (records_by_user or {}).items() if r}
    if not data:
        raise GraphError("There are no records to plot.")

    try:
        fig = Figure(figsize=(8, 4.6), dpi=100, facecolor="white")
        ax = fig.add_subplot(111)

        all_values = []
        for index, (username, records) in enumerate(data.items()):
            dates = [datetime.strptime(r["recorded_at"], DATE_FORMAT) for r in records]
            values = [r["bmi"] for r in records]
            all_values.extend(values)
            color = LINE_COLORS[index % len(LINE_COLORS)]
            ax.plot(dates, values, marker="o", linewidth=2.2, markersize=6,
                    color=color, label=f"{username} ({len(records)} records)", zorder=3)
            if len(data) == 1 and len(values) <= 15:  # label points on single-user charts
                for d, v in zip(dates, values):
                    ax.annotate(f"{v:.1f}", (d, v), textcoords="offset points",
                                xytext=(0, 9), ha="center", fontsize=8, color=color)

        # Colour-coded BMI category bands and threshold lines
        for low, high, category in BANDS:
            ax.axhspan(low, high, color=CATEGORY_COLORS[category], alpha=0.09, zorder=1)
        for threshold in (18.5, 25, 30):
            ax.axhline(threshold, color="#94A3B8", linestyle="--", linewidth=0.8, zorder=2)

        ax.set_ylim(max(10, min(all_values) - 3), min(60, max(max(all_values) + 3, 26)))
        locator = mdates.AutoDateLocator()
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))

        title = (f"BMI Trend - {next(iter(data))}" if len(data) == 1
                 else "BMI Trend - All Users")
        ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
        ax.set_xlabel("Date", fontsize=11)
        ax.set_ylabel("BMI", fontsize=11)
        ax.grid(True, alpha=0.25, zorder=0)

        handles, labels = ax.get_legend_handles_labels()
        handles += [Patch(facecolor=CATEGORY_COLORS[c], alpha=0.35) for c in CATEGORY_ORDER]
        labels += CATEGORY_ORDER
        ax.legend(handles, labels, loc="best", fontsize=8, framealpha=0.9)

        fig.tight_layout()
        return fig
    except Exception as exc:  # any matplotlib/date parsing problem
        raise GraphError(f"Could not generate the BMI trend graph: {exc}") from exc


def create_category_figure(counts):
    """Small bar chart of records per BMI category (used on the dashboard)."""
    try:
        fig = Figure(figsize=(4, 3.2), dpi=100, facecolor="white")
        ax = fig.add_subplot(111)
        values = [counts.get(c, 0) for c in CATEGORY_ORDER]
        bars = ax.bar(CATEGORY_ORDER, values,
                      color=[CATEGORY_COLORS[c] for c in CATEGORY_ORDER])
        for bar, value in zip(bars, values):
            ax.annotate(str(value), (bar.get_x() + bar.get_width() / 2, value),
                        textcoords="offset points", xytext=(0, 3),
                        ha="center", fontsize=9)
        ax.set_ylabel("Records")
        ax.set_ylim(0, max(values + [1]) * 1.2)
        ax.tick_params(axis="x", labelsize=8)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        fig.tight_layout()
        return fig
    except Exception as exc:
        raise GraphError(f"Could not generate the category chart: {exc}") from exc


def save_figure(fig, path):
    """Save a figure to PNG/PDF/SVG depending on the file extension."""
    try:
        fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    except Exception as exc:
        raise GraphError(f"Could not save the graph: {exc}") from exc
