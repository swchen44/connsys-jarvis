#!/usr/bin/env python3
"""Generate a professional HTML report from session analysis JSON.

Reads report.json (output of analyze_session.py) and produces a
standalone HTML file with interactive charts, summary cards, and
detailed statistics tables.

Usage:
    python3 generate_html_report.py <report.json> [--output <report.html>]

Or use together with analyze_session.py:
    python3 analyze_session.py <session.jsonl> -o /tmp/report/
    python3 generate_html_report.py /tmp/report/report.json

Requires: Python 3.10+ (stdlib only — charts rendered via inline SVG)
"""

import argparse
import html
import json
import logging
import math
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------

COLORS = {
    "primary": "#6366f1",     # indigo
    "success": "#22c55e",     # green
    "warning": "#f59e0b",     # amber
    "danger": "#ef4444",      # red
    "info": "#3b82f6",        # blue
    "muted": "#94a3b8",       # slate
}

PHASE_COLORS = {
    "understanding": "#8b5cf6",  # violet
    "designing": "#6366f1",      # indigo
    "exploring": "#3b82f6",      # blue
    "implementing": "#22c55e",   # green
    "debugging": "#ef4444",      # red
    "verifying": "#f59e0b",      # amber
}

CHART_COLORS = [
    "#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#3b82f6",
    "#8b5cf6", "#ec4899", "#14b8a6", "#f97316", "#64748b",
    "#a855f7", "#06b6d4", "#84cc16", "#e11d48", "#0ea5e9",
]


# ---------------------------------------------------------------------------
# SVG chart generators
# ---------------------------------------------------------------------------

def svg_donut(data: list[tuple[str, float, str]], size: int = 180, hole: float = 0.6) -> str:
    """Generate an SVG donut chart.

    Args:
        data: List of (label, value, color) tuples.
        size: SVG width/height.
        hole: Inner radius ratio (0-1).

    Returns:
        SVG markup string.
    """
    total = sum(v for _, v, _ in data)
    if total == 0:
        return '<svg></svg>'

    cx, cy = size / 2, size / 2
    r_outer = size / 2 - 5
    r_inner = r_outer * hole
    paths = []
    start_angle = -90  # Start from top

    for label, value, color in data:
        if value == 0:
            continue
        pct = value / total
        end_angle = start_angle + pct * 360
        large_arc = 1 if pct > 0.5 else 0

        # Outer arc
        x1o = cx + r_outer * math.cos(math.radians(start_angle))
        y1o = cy + r_outer * math.sin(math.radians(start_angle))
        x2o = cx + r_outer * math.cos(math.radians(end_angle))
        y2o = cy + r_outer * math.sin(math.radians(end_angle))

        # Inner arc (reverse)
        x1i = cx + r_inner * math.cos(math.radians(end_angle))
        y1i = cy + r_inner * math.sin(math.radians(end_angle))
        x2i = cx + r_inner * math.cos(math.radians(start_angle))
        y2i = cy + r_inner * math.sin(math.radians(start_angle))

        d = (
            f"M {x1o:.1f} {y1o:.1f} "
            f"A {r_outer:.1f} {r_outer:.1f} 0 {large_arc} 1 {x2o:.1f} {y2o:.1f} "
            f"L {x1i:.1f} {y1i:.1f} "
            f"A {r_inner:.1f} {r_inner:.1f} 0 {large_arc} 0 {x2i:.1f} {y2i:.1f} Z"
        )
        tooltip = f"{label}: {value:,.0f} ({pct:.1%})"
        paths.append(
            f'<path d="{d}" fill="{color}" stroke="white" stroke-width="1.5">'
            f'<title>{tooltip}</title></path>'
        )
        start_angle = end_angle

    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
        + "".join(paths)
        + '</svg>'
    )


def svg_bar_horizontal(data: list[tuple[str, float, str]], width: int = 400, bar_h: int = 28) -> str:
    """Generate horizontal bar chart SVG.

    Args:
        data: List of (label, value, color) tuples.
        width: Total SVG width.
        bar_h: Height per bar.

    Returns:
        SVG markup string.
    """
    if not data:
        return '<svg></svg>'

    max_val = max(v for _, v, _ in data) or 1
    label_w = 140
    chart_w = width - label_w - 80
    height = len(data) * (bar_h + 8) + 10
    bars = []

    for i, (label, value, color) in enumerate(data):
        y = i * (bar_h + 8) + 5
        bar_width = (value / max_val) * chart_w
        display_label = label[:18] + "..." if len(label) > 18 else label

        bars.append(
            f'<text x="{label_w - 8}" y="{y + bar_h/2 + 4}" '
            f'text-anchor="end" font-size="12" fill="#475569">{html.escape(display_label)}</text>'
        )
        bars.append(
            f'<rect x="{label_w}" y="{y}" width="{max(bar_width, 2):.1f}" '
            f'height="{bar_h}" rx="4" fill="{color}" opacity="0.85">'
            f'<title>{label}: {value:,.0f}</title></rect>'
        )
        bars.append(
            f'<text x="{label_w + bar_width + 6:.1f}" y="{y + bar_h/2 + 4}" '
            f'font-size="11" fill="#64748b">{value:,.0f}</text>'
        )

    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        + "".join(bars)
        + '</svg>'
    )


# ---------------------------------------------------------------------------
# HTML components
# ---------------------------------------------------------------------------

def card(title: str, value: str, subtitle: str = "", color: str = COLORS["primary"]) -> str:
    """Summary card component."""
    return f'''
    <div class="card">
      <div class="card-title">{html.escape(title)}</div>
      <div class="card-value" style="color:{color}">{value}</div>
      <div class="card-subtitle">{html.escape(subtitle)}</div>
    </div>'''


def section(title: str, content: str, section_id: str = "") -> str:
    """Report section with title."""
    id_attr = f' id="{section_id}"' if section_id else ''
    return f'''
    <section class="report-section"{id_attr}>
      <h2>{html.escape(title)}</h2>
      {content}
    </section>'''


def table(headers: list[str], rows: list[list[str]], highlight_col: int = -1) -> str:
    """Generate an HTML table."""
    ths = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    trs = []
    for row in rows:
        tds = []
        for i, cell in enumerate(row):
            cls = ' class="highlight"' if i == highlight_col else ''
            tds.append(f"<td{cls}>{cell}</td>")
        trs.append("<tr>" + "".join(tds) + "</tr>")
    return f'<table><thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table>'


def legend(items: list[tuple[str, str]]) -> str:
    """Chart legend component."""
    parts = []
    for label, color in items:
        parts.append(
            f'<span class="legend-item">'
            f'<span class="legend-dot" style="background:{color}"></span>'
            f'{html.escape(label)}</span>'
        )
    return f'<div class="legend">{"".join(parts)}</div>'


def progress_bar(value: float, color: str = COLORS["success"], label: str = "") -> str:
    """CSS progress bar."""
    pct = max(0, min(100, value * 100))
    return (
        f'<div class="progress-bar">'
        f'<div class="progress-fill" style="width:{pct:.1f}%;background:{color}"></div>'
        f'<span class="progress-label">{label or f"{pct:.1f}%"}</span>'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# Report sections
# ---------------------------------------------------------------------------

def build_summary(report: dict) -> str:
    """Build summary cards section."""
    l1 = report.get("L1_quality", {})
    meta = report.get("metadata", {})

    total_tokens = l1.get("total_tokens", 0)
    cost = l1.get("estimated_cost_usd", 0)
    cache_hit = l1.get("cache_hit_ratio", 0)
    effective = l1.get("effective_ratio", 0)
    duration = meta.get("duration_seconds", 0)
    tool_calls = l1.get("total_tool_calls", 0)
    tool_errors = l1.get("total_tool_errors", 0)

    cards = [
        card("Total Tokens", f"{total_tokens:,}", f"${cost:.4f} estimated", COLORS["primary"]),
        card("Cache Hit", f"{cache_hit:.1%}", "cache_read / total_input", COLORS["success"] if cache_hit > 0.7 else COLORS["warning"]),
        card("Effective", f"{effective:.1%}", "non-wasted tokens", COLORS["success"] if effective > 0.9 else COLORS["danger"]),
        card("Duration", f"{duration/60:.1f} min", f"{duration:.0f} seconds", COLORS["info"]),
        card("Tool Calls", f"{tool_calls:,}", f"{tool_errors} errors ({tool_errors/max(tool_calls,1):.0%})", COLORS["danger"] if tool_errors > tool_calls * 0.1 else COLORS["muted"]),
        card("API Errors", str(l1.get("api_error_count", 0)), f"{l1.get('compact_count', 0)} compactions", COLORS["danger"] if l1.get("api_error_count", 0) > 0 else COLORS["success"]),
    ]
    return '<div class="card-grid">' + "".join(cards) + '</div>'


def build_ai_summary(report: dict) -> str:
    """Build AI-generated summary text."""
    l1 = report.get("L1_quality", {})
    l3 = report.get("L3_behavior", {})
    meta = report.get("metadata", {})

    total = l1.get("total_tokens", 0)
    cost = l1.get("estimated_cost_usd", 0)
    cache = l1.get("cache_hit_ratio", 0)
    effective = l1.get("effective_ratio", 0)
    wasted = l1.get("wasted_ratio", 0) if "wasted_ratio" in l1 else (1 - effective)
    duration = meta.get("duration_seconds", 0)
    models = l1.get("models_seen", [])
    phases = l3.get("phases", [])
    waste = l3.get("waste_details", [])

    # Determine top phase
    top_phase = phases[0]["phase"] if phases else "unknown"
    top_ratio = phases[0]["ratio"] if phases else 0

    # Build summary points
    points = []
    points.append(f"Session consumed <strong>{total:,}</strong> tokens (~${cost:.2f}) over <strong>{duration/60:.1f} minutes</strong>.")

    if len(models) > 1:
        points.append(f"Models used: {', '.join(f'<code>{m}</code>' for m in models)}.")
    elif models:
        points.append(f"Model: <code>{models[0]}</code>.")

    if cache > 0.8:
        points.append(f"Excellent cache efficiency at <strong>{cache:.1%}</strong> — prompt cache is well utilized.")
    elif cache > 0.5:
        points.append(f"Moderate cache hit ratio ({cache:.1%}). Consider reducing context changes to improve cache reuse.")
    else:
        points.append(f"Low cache hit ratio ({cache:.1%}). Frequent context changes are invalidating the prompt cache.")

    points.append(f"AI spent <strong>{top_ratio:.0%}</strong> of tokens on <em>{top_phase}</em>.")

    if wasted > 0.05:
        waste_types = set(w.get("waste_type", "") for w in waste)
        points.append(f'<span style="color:{COLORS["danger"]}">Token waste at {wasted:.1%} — types: {", ".join(waste_types)}. Review the waste details below.</span>')
    elif wasted > 0.01:
        points.append(f"Minor token waste ({wasted:.1%}) — within acceptable range.")
    else:
        points.append(f'<span style="color:{COLORS["success"]}">Minimal waste ({wasted:.1%}) — very clean session.</span>')

    tool_errors = l1.get("total_tool_errors", 0)
    if tool_errors > 5:
        points.append(f'<span style="color:{COLORS["danger"]}">{tool_errors} tool errors detected. Check the Tool Statistics table for details.</span>')

    items = "".join(f"<li>{p}</li>" for p in points)
    return f'<div class="summary-box"><h3>Session Summary</h3><ul>{items}</ul></div>'


def build_token_distribution(report: dict) -> str:
    """Build token distribution donut chart."""
    tokens = report.get("L2_statistics", {}).get("tokens", {}).get("total", {})
    if not tokens:
        return "<p>No token data available.</p>"

    data = [
        ("Input", tokens.get("input_tokens", 0), CHART_COLORS[0]),
        ("Output", tokens.get("output_tokens", 0), CHART_COLORS[1]),
        ("Cache Create", tokens.get("cache_creation_tokens", 0), CHART_COLORS[2]),
        ("Cache Read", tokens.get("cache_read_tokens", 0), CHART_COLORS[3]),
    ]

    chart = svg_donut(data, size=200)
    leg = legend([(label, color) for label, _, color in data])

    # Numbers table
    rows = []
    for label, value, _ in data:
        total = sum(v for _, v, _ in data)
        pct = value / max(total, 1)
        rows.append([label, f"{value:,}", f"{pct:.1%}"])
    tbl = table(["Category", "Tokens", "Ratio"], rows)

    return f'''
    <div class="chart-row">
      <div class="chart-container">{chart}{leg}</div>
      <div class="chart-table">{tbl}</div>
    </div>'''


def build_model_distribution(report: dict) -> str:
    """Build model usage distribution."""
    per_model = report.get("L2_statistics", {}).get("tokens", {}).get("per_model", {})
    if not per_model:
        return "<p>No model data.</p>"

    data = []
    rows = []
    for i, (model, info) in enumerate(sorted(per_model.items(), key=lambda x: x[1].get("output_tokens", 0), reverse=True)):
        total = info.get("input_tokens", 0) + info.get("output_tokens", 0) + info.get("cache_creation_tokens", 0) + info.get("cache_read_tokens", 0)
        cost = info.get("cost_usd", 0)
        color = CHART_COLORS[i % len(CHART_COLORS)]
        data.append((model.split("-")[1] if "-" in model else model, total, color))
        rows.append([f'<code>{html.escape(model)}</code>', f"{total:,}", f"${cost:.4f}"])

    chart = svg_bar_horizontal(data, width=500)
    tbl = table(["Model", "Tokens", "Cost"], rows)

    return f'<div class="chart-row"><div class="chart-container">{chart}</div><div class="chart-table">{tbl}</div></div>'


def build_tool_stats(report: dict) -> str:
    """Build tool statistics table with bar chart."""
    tools = report.get("L2_statistics", {}).get("tools", {}).get("tools", [])
    if not tools:
        return "<p>No tool data.</p>"

    # Bar chart
    data = [(t["name"], t["calls"], CHART_COLORS[i % len(CHART_COLORS)]) for i, t in enumerate(tools[:12])]
    chart = svg_bar_horizontal(data, width=500)

    # Table
    rows = []
    for t in tools:
        err_cls = f' style="color:{COLORS["danger"]};font-weight:600"' if t["errors"] > 0 else ''
        rows.append([
            f'<code>{html.escape(t["name"])}</code>',
            str(t["calls"]),
            str(t["success"]),
            f'<span{err_cls}>{t["errors"]}</span>',
            f'{t["error_rate"]:.0%}',
            f'{t["tokens"]:,}',
            f'{t["ratio"]:.1%}',
        ])
    tbl = table(["Tool", "Calls", "OK", "Err", "Err%", "Tokens", "Share"], rows)

    return f'<div class="chart-row"><div class="chart-container">{chart}</div><div class="chart-table" style="flex:1.5">{tbl}</div></div>'


def build_behavior_phases(report: dict) -> str:
    """Build behavior phase analysis."""
    phases = report.get("L3_behavior", {}).get("phases", [])
    if not phases:
        return "<p>No behavior data.</p>"

    # Horizontal stacked bar (CSS-based for simplicity)
    total = sum(p["tokens"] for p in phases)
    segments = []
    for p in phases:
        pct = (p["tokens"] / max(total, 1)) * 100
        color = PHASE_COLORS.get(p["phase"], COLORS["muted"])
        if pct > 3:  # Only show label if wide enough
            segments.append(
                f'<div class="phase-segment" style="width:{pct:.1f}%;background:{color}" '
                f'title="{p["phase"]}: {p["tokens"]:,} tokens ({pct:.1f}%)">'
                f'<span>{p["phase"][:4]}</span></div>'
            )
        else:
            segments.append(
                f'<div class="phase-segment" style="width:{pct:.1f}%;background:{color}" '
                f'title="{p["phase"]}: {p["tokens"]:,} tokens ({pct:.1f}%)"></div>'
            )

    stacked_bar = f'<div class="stacked-bar">{"".join(segments)}</div>'
    leg = legend([(p["phase"], PHASE_COLORS.get(p["phase"], COLORS["muted"])) for p in phases])

    # Phase table
    rows = []
    for p in phases:
        color = PHASE_COLORS.get(p["phase"], COLORS["muted"])
        bar = progress_bar(p["ratio"], color, f'{p["ratio"]:.1%}')
        rows.append([
            f'<span style="color:{color};font-weight:600">{p["phase"]}</span>',
            str(p["message_count"]),
            f'{p["tokens"]:,}',
            bar,
        ])
    tbl = table(["Phase", "Messages", "Tokens", "Distribution"], rows)

    return f'{stacked_bar}{leg}<div style="margin-top:16px">{tbl}</div>'


def build_efficiency(report: dict) -> str:
    """Build token efficiency visualization."""
    eff = report.get("L3_behavior", {}).get("efficiency", {})
    if not eff:
        return ""

    effective = eff.get("effective_tokens", 0)
    wasted = eff.get("wasted_tokens", 0)
    total = eff.get("total_tokens", 1)

    donut_data = [
        ("Effective", effective, COLORS["success"]),
        ("Wasted", wasted, COLORS["danger"]),
    ]
    chart = svg_donut(donut_data, size=160, hole=0.65)
    leg = legend([("Effective", COLORS["success"]), ("Wasted", COLORS["danger"])])

    # Waste details
    waste = report.get("L3_behavior", {}).get("waste_details", [])
    waste_html = ""
    if waste:
        rows = [[w["waste_type"], w["description"], f'{w["tokens"]:,}'] for w in waste[:15]]
        waste_html = '<h3 style="margin-top:20px">Waste Details</h3>' + table(["Type", "Description", "Tokens"], rows)

    return f'''
    <div class="chart-row">
      <div class="chart-container">
        {chart}{leg}
        <div style="text-align:center;margin-top:8px;font-size:14px;color:#64748b">
          {effective:,} effective / {wasted:,} wasted
        </div>
      </div>
      <div class="chart-table">{waste_html}</div>
    </div>'''


def build_errors_hooks(report: dict) -> str:
    """Build errors and hooks section."""
    parts = []

    # API errors
    errors = report.get("L2_statistics", {}).get("errors", {})
    if errors.get("error_count", 0) > 0:
        dist = errors.get("error_code_distribution", {})
        rows = [[code, str(count)] for code, count in dist.items()]
        parts.append(f'<h3>API Errors ({errors["error_count"]} total, {errors["retry_count"]} retries)</h3>')
        parts.append(table(["Error Code", "Count"], rows))

    # Hooks
    hooks = report.get("L2_statistics", {}).get("hooks", {}).get("hooks", [])
    if hooks:
        rows = [[h["event"], str(h["count"]), f'{h["avg_duration_ms"]:.0f}ms', str(h.get("exit_codes", {}))] for h in hooks]
        parts.append('<h3>Hook Execution</h3>')
        parts.append(table(["Event", "Count", "Avg Duration", "Exit Codes"], rows))

    # Stop reasons
    stop = report.get("L3_behavior", {}).get("stop_reason_distribution", {})
    if stop:
        rows = [[reason, str(count)] for reason, count in stop.items()]
        parts.append('<h3>Stop Reasons</h3>')
        parts.append(table(["Reason", "Count"], rows))

    return "".join(parts) if parts else "<p>No errors or hooks recorded.</p>"


def build_session_info(report: dict) -> str:
    """Build session metadata section."""
    meta = report.get("metadata", {})
    rows = [
        ["Session ID", f'<code>{meta.get("session_id", "")[:24]}...</code>'],
        ["Claude Code Version", meta.get("version", "")],
        ["Git Branch", f'<code>{meta.get("git_branch", "")}</code>'],
        ["Working Directory", f'<code>{meta.get("cwd", "")}</code>'],
        ["Start", meta.get("first_timestamp", "")],
        ["End", meta.get("last_timestamp", "")],
        ["Duration", f'{meta.get("duration_seconds", 0)/60:.1f} minutes'],
        ["Total JSONL Lines", f'{meta.get("total_lines", 0):,}'],
    ]
    return table(["Field", "Value"], rows)


# ---------------------------------------------------------------------------
# Main HTML assembly
# ---------------------------------------------------------------------------

CSS = """
:root {
  --bg: #f8fafc; --card-bg: #ffffff; --border: #e2e8f0;
  --text: #1e293b; --text-secondary: #64748b; --radius: 12px;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg); color: var(--text); line-height: 1.6;
  max-width: 1200px; margin: 0 auto; padding: 24px;
}
h1 { font-size: 28px; font-weight: 700; margin-bottom: 8px; }
h2 { font-size: 20px; font-weight: 600; margin-bottom: 16px; color: #334155; border-bottom: 2px solid var(--border); padding-bottom: 8px; }
h3 { font-size: 16px; font-weight: 600; margin-bottom: 10px; color: #475569; }
.header { margin-bottom: 32px; }
.header-sub { color: var(--text-secondary); font-size: 14px; }
.card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 16px; margin-bottom: 32px; }
.card {
  background: var(--card-bg); border-radius: var(--radius); padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid var(--border);
}
.card-title { font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-secondary); margin-bottom: 4px; }
.card-value { font-size: 28px; font-weight: 700; line-height: 1.2; }
.card-subtitle { font-size: 12px; color: var(--text-secondary); margin-top: 4px; }
.summary-box {
  background: linear-gradient(135deg, #eff6ff 0%, #f0fdf4 100%);
  border: 1px solid #bfdbfe; border-radius: var(--radius); padding: 20px; margin-bottom: 32px;
}
.summary-box h3 { color: #1e40af; margin-bottom: 10px; }
.summary-box ul { padding-left: 20px; }
.summary-box li { margin-bottom: 6px; font-size: 14px; color: #334155; }
.report-section {
  background: var(--card-bg); border-radius: var(--radius); padding: 24px;
  margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  border: 1px solid var(--border);
}
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; padding: 10px 12px; background: #f1f5f9; color: #475569; font-weight: 600; border-bottom: 2px solid var(--border); }
td { padding: 8px 12px; border-bottom: 1px solid var(--border); }
tr:hover { background: #f8fafc; }
td.highlight { font-weight: 600; }
code { background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 12px; color: #6366f1; }
.chart-row { display: flex; gap: 24px; align-items: flex-start; flex-wrap: wrap; }
.chart-container { flex-shrink: 0; text-align: center; }
.chart-table { flex: 1; min-width: 300px; overflow-x: auto; }
.legend { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 12px; justify-content: center; }
.legend-item { display: flex; align-items: center; gap: 4px; font-size: 12px; color: var(--text-secondary); }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.stacked-bar { display: flex; height: 40px; border-radius: 8px; overflow: hidden; margin-bottom: 8px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); }
.phase-segment { display: flex; align-items: center; justify-content: center; color: white; font-size: 11px; font-weight: 600; cursor: default; transition: opacity 0.2s; }
.phase-segment:hover { opacity: 0.85; }
.progress-bar { background: #e2e8f0; border-radius: 6px; height: 20px; position: relative; overflow: hidden; min-width: 120px; }
.progress-fill { height: 100%; border-radius: 6px; transition: width 0.3s; }
.progress-label { position: absolute; right: 6px; top: 50%; transform: translateY(-50%); font-size: 11px; font-weight: 600; color: #334155; }
.nav { position: sticky; top: 0; background: var(--bg); padding: 12px 0; z-index: 10; margin-bottom: 16px; display: flex; gap: 8px; flex-wrap: wrap; }
.nav a { padding: 6px 14px; border-radius: 8px; font-size: 13px; color: #475569; text-decoration: none; background: var(--card-bg); border: 1px solid var(--border); transition: all 0.2s; }
.nav a:hover { background: #6366f1; color: white; border-color: #6366f1; }
@media (max-width: 768px) { .chart-row { flex-direction: column; } .card-grid { grid-template-columns: repeat(2, 1fr); } }
.footer { text-align: center; color: var(--text-secondary); font-size: 12px; padding: 24px 0; }
"""


def generate_html(report: dict) -> str:
    """Generate complete HTML report.

    Args:
        report: Parsed report.json data.

    Returns:
        Complete HTML string.
    """
    meta = report.get("metadata", {})
    session_id = meta.get("session_id", "unknown")[:16]
    timestamp = meta.get("first_timestamp", "")[:19]

    body_parts = [
        f'''<div class="header">
          <h1>Session Analysis Report</h1>
          <div class="header-sub">Session {session_id}... &mdash; {timestamp}</div>
        </div>''',

        '<nav class="nav">'
        '<a href="#summary">Summary</a>'
        '<a href="#tokens">Tokens</a>'
        '<a href="#models">Models</a>'
        '<a href="#tools">Tools</a>'
        '<a href="#behavior">Behavior</a>'
        '<a href="#efficiency">Efficiency</a>'
        '<a href="#errors">Errors & Hooks</a>'
        '<a href="#info">Session Info</a>'
        '</nav>',

        build_summary(report),
        f'<div id="summary">{build_ai_summary(report)}</div>',
        section("Token Distribution", build_token_distribution(report), "tokens"),
        section("Model Usage", build_model_distribution(report), "models"),
        section("Tool Statistics", build_tool_stats(report), "tools"),
        section("Behavior Phases", build_behavior_phases(report), "behavior"),
        section("Token Efficiency", build_efficiency(report), "efficiency"),
        section("Errors & Hooks", build_errors_hooks(report), "errors"),
        section("Session Info", build_session_info(report), "info"),

        '<div class="footer">Generated by framework-session-analyzer-tool &mdash; connsys-jarvis</div>',
    ]

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Session Report — {session_id}</title>
<style>{CSS}</style>
</head>
<body>
{"".join(body_parts)}
</body>
</html>"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate HTML report from session analysis JSON")
    parser.add_argument("report_json", help="Path to report.json (from analyze_session.py)")
    parser.add_argument("--output", "-o", help="Output HTML path (default: report.html in same dir)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    json_path = Path(args.report_json)
    if not json_path.exists():
        logger.error("File not found: %s", json_path)
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as fh:
        report = json.load(fh)

    html_content = generate_html(report)

    output_path = Path(args.output) if args.output else json_path.with_name("report.html")
    output_path.write_text(html_content, encoding="utf-8")
    logger.info("HTML report: %s", output_path)

    print(f"Report generated: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
