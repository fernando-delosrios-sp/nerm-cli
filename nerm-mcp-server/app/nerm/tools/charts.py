from __future__ import annotations

import base64
import json
import logging
import math
from io import BytesIO
from datetime import datetime
from typing import Any

from nerm.config import get_settings
from mcp.types import CallToolResult, ImageContent, TextContent
from nerm.tools.tool_guidance import CHART_USAGE, append_tool_guidance

CHART_TYPES: set[str] = {
    "line",
    "bar",
    "pie",
    "donut",
    "scatter",
    "area",
    "horizontal_bar",
    "histogram",
    "box",
    "grouped_bar",
    "stacked_bar",
    "multi_line",
    "heatmap",
}
CHART_TYPE_ALIASES: dict[str, str] = {
    "hbar": "horizontal_bar",
    "horizontalbar": "horizontal_bar",
    "boxplot": "box",
    "stacked": "stacked_bar",
    "grouped": "grouped_bar",
    "multi": "multi_line",
    "multiline": "multi_line",
    "pie": "pie",
    "piechart": "pie",
    "donut": "donut",
    "donutchart": "donut",
    "scatter": "scatter",
    "scatterplot": "scatter",
    "area": "area",
    "areachart": "area",
    "heatmap": "heatmap",
    "heatmapchart": "heatmap",
}
_LOGGER = logging.getLogger("nerm.tools.charts")
VALID_LEGEND_POSITIONS: set[str] = {
    "best",
    "upper right",
    "upper left",
    "lower left",
    "lower right",
    "right",
    "center left",
    "center right",
    "lower center",
    "upper center",
    "center",
}


def _extract_xy(entry: dict) -> tuple[list[object], list[float]]:
    points = entry.get("points")
    if isinstance(points, list):
        x_vals: list[object] = []
        y_vals: list[float] = []
        for point in points:
            if isinstance(point, dict) and "y" in point:
                y_raw = point["y"]
                x_raw = point.get("x", len(x_vals))
            elif isinstance(point, (list, tuple)) and len(point) >= 2:
                x_raw, y_raw = point[0], point[1]
            else:
                continue
            try:
                y = float(y_raw)
            except (TypeError, ValueError):
                continue
            x_vals.append(x_raw)
            y_vals.append(y)
        if y_vals:
            return x_vals, y_vals

    x_raw = entry.get("x")
    y_raw = entry.get("y")
    if isinstance(y_raw, list):
        y_vals = []
        for value in y_raw:
            try:
                y_vals.append(float(value))
            except (TypeError, ValueError):
                continue
        if not y_vals:
            return [], []
        if isinstance(x_raw, list) and len(x_raw) == len(y_vals):
            return list(x_raw), y_vals
        return list(range(len(y_vals))), y_vals

    values = entry.get("values")
    if isinstance(values, list):
        y_vals = []
        for value in values:
            try:
                y_vals.append(float(value))
            except (TypeError, ValueError):
                continue
        if y_vals:
            return list(range(len(y_vals))), y_vals

    return [], []


def _parse_color(value: str, param_name: str) -> str:
    from matplotlib.colors import is_color_like

    color = value.strip()
    if not color:
        raise ValueError(f"{param_name} must be a non-empty color string")
    if not is_color_like(color):
        raise ValueError(f"{param_name} must be a valid matplotlib color, got {value!r}")
    return color


def _resolve_optional_color(value: str | None, param_name: str) -> str | None:
    if value is None or not value.strip():
        return None
    return _parse_color(value, param_name)


def _parse_series_colors(series_colors: str | list[str] | None) -> list[str]:
    if series_colors is None:
        return []
    if isinstance(series_colors, str):
        raw_colors = [part.strip() for part in series_colors.split(",") if part.strip()]
    elif isinstance(series_colors, list):
        raw_colors = [str(part).strip() for part in series_colors if str(part).strip()]
    else:
        raise ValueError("series_colors must be a comma-separated string or list of colors.")
    return [_parse_color(color, "series_colors") for color in raw_colors]


def _resolve_legend_position(legend_position: str | None) -> str:
    if legend_position is None or not legend_position.strip():
        return "best"
    normalized = legend_position.strip().lower().replace("_", " ")
    if normalized not in VALID_LEGEND_POSITIONS:
        allowed = ", ".join(sorted(VALID_LEGEND_POSITIONS))
        raise ValueError(f"legend_position must be one of: {allowed}")
    return normalized


def _series_color(series_colors: list[str], idx: int) -> str | None:
    if 0 <= idx < len(series_colors):
        return series_colors[idx]
    return None


def _downsample_xy(x_vals: list[object], y_vals: list[float], max_points: int) -> tuple[list[object], list[float]]:
    if max_points <= 0 or len(y_vals) <= max_points:
        return x_vals, y_vals
    if max_points == 1:
        return [x_vals[0]], [y_vals[0]]
    span = len(y_vals) - 1
    step = span / (max_points - 1)
    indices: list[int] = []
    for i in range(max_points):
        idx = int(round(i * step))
        if not indices or idx != indices[-1]:
            indices.append(idx)
    return [x_vals[i] for i in indices], [y_vals[i] for i in indices]


def _parse_date_like(value: object) -> datetime | None:
    text = str(value).strip()
    if not text:
        return None
    candidates = [text]
    if text.endswith("Z"):
        candidates.append(text[:-1] + "+00:00")
    # Treat YYYY-MM as first day-of-month for timeline sorting.
    if len(text) == 7 and text[4] == "-":
        candidates.append(f"{text}-01")
    for candidate in candidates:
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            continue
    return None


def _sort_xy_if_date_based(
    x_vals: list[object],
    y_vals: list[float],
    *,
    sort_x: bool | None,
) -> tuple[list[object], list[float], bool]:
    if len(x_vals) != len(y_vals) or len(x_vals) < 2:
        return x_vals, y_vals, False
    if sort_x is False:
        return x_vals, y_vals, False
    parsed = [_parse_date_like(x) for x in x_vals]
    if any(item is None for item in parsed):
        if sort_x is True:
            paired = sorted(zip([str(x) for x in x_vals], x_vals, y_vals), key=lambda item: item[0])
            return [item[1] for item in paired], [item[2] for item in paired], True
        return x_vals, y_vals, False
    paired = sorted(zip(parsed, x_vals, y_vals), key=lambda item: item[0])  # type: ignore[arg-type]
    sorted_x = [item[1] for item in paired]
    sorted_y = [item[2] for item in paired]
    return sorted_x, sorted_y, True


def _normalize_chart_type(value: object) -> str:
    raw = str(value or "line").strip().lower()
    compact = raw.replace("-", "_").replace(" ", "")
    if compact.endswith("chart"):
        compact = compact[: -len("chart")]
    chart_type = CHART_TYPE_ALIASES.get(compact, raw.replace("-", "_").replace(" ", "_"))
    if chart_type not in CHART_TYPES:
        return "line"
    return chart_type


def _extract_heatmap(entry: dict) -> tuple[list[list[float]], list[str], list[str]]:
    matrix_raw = entry.get("matrix")
    if not isinstance(matrix_raw, list) or not matrix_raw:
        return [], [], []
    matrix: list[list[float]] = []
    for row in matrix_raw:
        if not isinstance(row, list) or not row:
            continue
        parsed_row: list[float] = []
        for value in row:
            try:
                parsed_row.append(float(value))
            except (TypeError, ValueError):
                parsed_row.append(0.0)
        matrix.append(parsed_row)
    if not matrix:
        return [], [], []
    width = min(len(r) for r in matrix)
    if width <= 0:
        return [], [], []
    matrix = [r[:width] for r in matrix]
    x_labels = [str(v) for v in (entry.get("x_labels") or [])]
    y_labels = [str(v) for v in (entry.get("y_labels") or [])]
    if len(x_labels) != width:
        x_labels = [str(i) for i in range(width)]
    if len(y_labels) != len(matrix):
        y_labels = [str(i) for i in range(len(matrix))]
    return matrix, x_labels, y_labels


def _render_single_series(
    ax: object,
    idx: int,
    entry: dict,
    max_points: int,
    *,
    sort_x: bool | None,
    series_colors: list[str],
    transparency: float,
) -> tuple[bool, bool]:
    x_vals, y_vals = _extract_xy(entry)
    if not y_vals:
        return False, False
    x_vals, y_vals, _ = _sort_xy_if_date_based(x_vals, y_vals, sort_x=sort_x)
    x_vals, y_vals = _downsample_xy(x_vals, y_vals, max_points=max_points)
    parsed_dates = [_parse_date_like(x) for x in x_vals]
    use_date_axis = all(item is not None for item in parsed_dates) and len(parsed_dates) > 0
    plot_x = parsed_dates if use_date_axis else x_vals
    chart_type = _normalize_chart_type(entry.get("chart_type", "line"))
    label = str(entry.get("label") or f"Series {idx + 1}")
    color = _series_color(series_colors, idx)
    alpha = transparency if transparency < 1.0 else None
    if chart_type == "bar":
        ax.bar(plot_x, y_vals, label=label, color=color, alpha=alpha)
    elif chart_type == "horizontal_bar":
        ax.barh([str(v) for v in x_vals], y_vals, label=label, color=color, alpha=alpha)
    elif chart_type == "scatter":
        if use_date_axis:
            ax.scatter(plot_x, y_vals, label=label, color=color, alpha=alpha)
        else:
            x_numeric: list[float] = []
            for i, x in enumerate(x_vals):
                try:
                    x_numeric.append(float(x))
                except (TypeError, ValueError):
                    x_numeric.append(float(i))
            ax.scatter(x_numeric, y_vals, label=label, color=color, alpha=alpha)
    elif chart_type == "area":
        fill_alpha = min(0.35, transparency) if transparency < 1.0 else 0.35
        if use_date_axis:
            ax.plot(plot_x, y_vals, label=label, color=color, alpha=alpha)
            ax.fill_between(plot_x, y_vals, alpha=fill_alpha, color=color)
        else:
            x_idx = list(range(len(y_vals)))
            ax.plot(x_idx, y_vals, label=label, color=color, alpha=alpha)
            ax.fill_between(x_idx, y_vals, alpha=fill_alpha, color=color)
            ax.set_xticks(x_idx, [str(v) for v in x_vals], rotation=45, ha="right")
    elif chart_type == "histogram":
        hist_alpha = min(0.7, transparency) if transparency < 1.0 else 0.7
        ax.hist(y_vals, bins=min(20, max(5, len(y_vals) // 2)), alpha=hist_alpha, label=label, color=color)
    elif chart_type == "box":
        ax.boxplot(y_vals, tick_labels=[label])
    elif chart_type in {"pie", "donut"}:
        labels = [str(v) for v in x_vals]
        wedgeprops = {"width": 0.45, "edgecolor": "white"} if chart_type == "donut" else None
        pie_kwargs: dict[str, Any] = {"labels": labels, "autopct": "%1.1f%%", "startangle": 90, "wedgeprops": wedgeprops}
        if color:
            pie_kwargs["colors"] = [color] * len(y_vals)
        ax.pie(y_vals, **pie_kwargs)
        ax.axis("equal")
    else:
        ax.plot(plot_x, y_vals, marker="o", label=label, color=color, alpha=alpha)
    return True, use_date_axis


def _render_multi_series(
    ax: object,
    series: list[dict],
    max_points: int,
    chart_type: str,
    *,
    sort_x: bool | None,
    series_colors: list[str],
    transparency: float,
) -> tuple[int, bool]:
    prepared: list[tuple[str, list[object], list[float]]] = []
    any_date_sorted = False
    any_date_axis = False
    for idx, entry in enumerate(series):
        x_vals, y_vals = _extract_xy(entry)
        if not y_vals:
            continue
        x_vals, y_vals, did_sort = _sort_xy_if_date_based(x_vals, y_vals, sort_x=sort_x)
        any_date_sorted = any_date_sorted or did_sort
        parsed_dates = [_parse_date_like(x) for x in x_vals]
        if all(item is not None for item in parsed_dates) and len(parsed_dates) > 0:
            any_date_axis = True
        x_vals, y_vals = _downsample_xy(x_vals, y_vals, max_points=max_points)
        label = str(entry.get("label") or f"Series {idx + 1}")
        prepared.append((label, x_vals, y_vals))
    if not prepared:
        return 0, False
    if chart_type == "multi_line":
        for i, (label, x_vals, y_vals) in enumerate(prepared):
            color = _series_color(series_colors, i)
            alpha = transparency if transparency < 1.0 else None
            parsed_dates = [_parse_date_like(x) for x in x_vals]
            if all(item is not None for item in parsed_dates) and len(parsed_dates) > 0:
                any_date_axis = True
                ax.plot(parsed_dates, y_vals, marker="o", label=label, color=color, alpha=alpha)
            else:
                ax.plot(x_vals, y_vals, marker="o", label=label, color=color, alpha=alpha)
        return len(prepared), any_date_axis
    x_labels = [str(v) for v in prepared[0][1]]
    if any_date_sorted:
        x_dt = [_parse_date_like(v) for v in x_labels]
        if all(dt is not None for dt in x_dt):
            order = sorted(range(len(x_labels)), key=lambda i: x_dt[i])  # type: ignore[index]
            x_labels = [x_labels[i] for i in order]
            reordered: list[tuple[str, list[object], list[float]]] = []
            for label, xs, ys in prepared:
                y_by_x = {str(x): y for x, y in zip(xs, ys)}
                reordered.append((label, x_labels, [y_by_x.get(x, 0.0) for x in x_labels]))
            prepared = reordered
    n = len(x_labels)
    x_idx = list(range(n))
    if chart_type == "grouped_bar":
        width = 0.8 / max(len(prepared), 1)
        for i, (label, _x, y_vals) in enumerate(prepared):
            shifted = [x + (i - (len(prepared) - 1) / 2) * width for x in x_idx]
            ax.bar(
                shifted,
                y_vals[:n],
                width=width,
                label=label,
                color=_series_color(series_colors, i),
                alpha=transparency if transparency < 1.0 else None,
            )
        ax.set_xticks(x_idx, x_labels, rotation=45, ha="right")
    else:
        bottoms = [0.0] * n
        for i, (label, _x, y_vals) in enumerate(prepared):
            vals = y_vals[:n]
            ax.bar(
                x_idx,
                vals,
                bottom=bottoms,
                label=label,
                color=_series_color(series_colors, i),
                alpha=transparency if transparency < 1.0 else None,
            )
            bottoms = [b + v for b, v in zip(bottoms, vals)]
        ax.set_xticks(x_idx, x_labels, rotation=45, ha="right")
    return len(prepared), any_date_axis


def _encode_png_with_budget(fig: object, start_dpi: int, min_dpi: int, target_png_bytes: int) -> tuple[bytes, int]:
    current_dpi = max(int(start_dpi), int(min_dpi))
    while True:
        buffer = BytesIO()
        fig.savefig(buffer, format="png", dpi=current_dpi)
        png_bytes = buffer.getvalue()
        if len(png_bytes) <= target_png_bytes or current_dpi <= min_dpi:
            return png_bytes, current_dpi
        next_dpi = max(min_dpi, int(current_dpi * 0.75))
        if next_dpi >= current_dpi:
            next_dpi = current_dpi - 1
        current_dpi = max(min_dpi, next_dpi)


def _truncate_tick(text: str, max_len: int = 24) -> str:
    text = str(text)
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _apply_readability_layout(
    fig: object,
    ax: object,
    chart_type: str,
    plotted: int,
    *,
    date_axis: bool,
    max_label_length: int | None,
    max_visible_ticks: int | None,
    label_rotation: int | None,
) -> None:
    if chart_type in {"pie", "donut", "heatmap"}:
        return

    resolved_max_label_length = 24 if max_label_length is None else max_label_length
    resolved_max_visible_ticks = 16 if max_visible_ticks is None else max_visible_ticks

    x_tick_labels = ax.get_xticklabels()
    visible_x = [label for label in x_tick_labels if label.get_text()]
    if visible_x:
        for label in visible_x:
            label.set_text(_truncate_tick(label.get_text(), max_len=resolved_max_label_length))

        tick_count = len(visible_x)
        if tick_count > 0:
            if (not date_axis) and tick_count > resolved_max_visible_ticks:
                step = int(math.ceil(tick_count / resolved_max_visible_ticks))
                for idx, label in enumerate(visible_x):
                    label.set_visible(idx % step == 0)

            if label_rotation is None:
                rotation = 0
                if tick_count > 8:
                    rotation = 45
                if tick_count > 12:
                    rotation = 60
            else:
                rotation = label_rotation
            if rotation:
                for label in visible_x:
                    label.set_rotation(rotation)
                    label.set_ha("right")

    y_tick_labels = ax.get_yticklabels()
    for label in y_tick_labels:
        if label.get_text():
            label.set_text(_truncate_tick(label.get_text(), max_len=resolved_max_label_length + 4))

    legend = ax.get_legend()
    if legend is not None and plotted > 3:
        ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), borderaxespad=0.0)

    fig.canvas.draw_idle()


def _error_result(error: str, message: str) -> CallToolResult:
    structured_error = {
        "status": "error",
        "error": error,
        "message": message,
        "guidance": "Verify chart arguments and provide plottable numeric series.",
        "details": {},
    }
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(structured_error, default=str))],
        structuredContent=structured_error,
        isError=True,
    )


def nerm_generate_chart(
    series: list[dict],
    embed_in_response: bool | None = None,
    include_base64: bool | None = None,
    title: str = "NERM Chart",
    x_label: str = "X",
    y_label: str = "Value",
    width: float = 8.0,
    height: float = 4.5,
    dpi: int = 160,
    min_dpi: int = 48,
    show_grid: bool = True,
    background_color: str | None = None,
    axes_background_color: str | None = None,
    text_color: str | None = None,
    axis_label_color: str | None = None,
    tick_label_color: str | None = None,
    font_family: str | None = None,
    font_size: float | None = None,
    legend_position: str | None = None,
    layout_pad: float | None = None,
    margin_left: float | None = None,
    margin_right: float | None = None,
    margin_top: float | None = None,
    margin_bottom: float | None = None,
    series_colors: str | list[str] | None = None,
    colormap: str | None = None,
    transparency: float | None = None,
    sort_x: bool | None = None,
    max_label_length: int | None = None,
    max_visible_ticks: int | None = None,
    label_rotation: int | None = None,
    max_points_per_series: int = 300,
    target_png_bytes: int = 350_000,
    return_markdown_data_url: bool = False,
) -> CallToolResult:
    """Render charts from numeric series and return serializable MCP content blocks.

    Use for visualization of already-computed results; this tool does not query NERM APIs.
    Options:
    - `series`: list of series dicts with optional `label`, `chart_type`, and data in one
      of these shapes: `points` (`[{x, y}]` or `[[x, y], ...]`), `x` + `y`, `values`,
      or heatmap `matrix`.
    - Supported chart types: `line`, `bar`, `pie`, `donut`, `scatter`, `area`,
      `horizontal_bar`, `histogram`, `box`, `grouped_bar`, `stacked_bar`,
      `multi_line`, `heatmap`.
    - `embed_in_response` / `include_base64`: compatibility args (not used for delivery mode).
    - Returns JSON-serializable MCP `content` blocks:
      `{"type":"text","text":"...json..."}` and `{"type":"image","mimeType":"image/png","data":"...base64..."}`.
    - Delivery uses MCP image content block semantics for wide client compatibility.
    - `return_markdown_data_url`: optional compatibility fallback for clients that do
      not render MCP image blocks. When true, metadata includes markdown data URL.
    - `title`, `x_label`, `y_label`, `width`, `height`, `dpi`, `show_grid`: chart styling.
    - Readability controls (optional, default auto):
      - `max_label_length`: truncate long labels to this length.
      - `max_visible_ticks`: show at most this many x-axis ticks.
      - `label_rotation`: one of `0`, `30`, `45`, `60`, `90`.
    - `sort_x`: `None` (auto), `True` (force sort), `False` (disable sorting).
    - If x-axis values are date-based (ISO date/date-time strings), sort chronologically
      before charting to ensure correct temporal presentation.
    - Use defaults unless labels overlap.
    - If overlap persists: set `max_visible_ticks` 8-12, `label_rotation` 45 or 60,
      and `max_label_length` 16-24.
    - Readability defaults are applied automatically for dense categorical charts:
      tick label truncation, tick downsampling, label rotation, and legend repositioning.
    - `max_points_per_series`: automatic per-series downsampling cap for payload control.
    - `target_png_bytes`: preferred PNG size target for adaptive downscaling.
      This is not a hard failure cap; oversized charts still return with a warning.
    """
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # noqa: BLE001
        return _error_result("chart_generation_error", f"matplotlib unavailable: {exc}")

    if not isinstance(series, list) or not series:
        return _error_result("invalid_chart_spec", "series must be a non-empty list of chart series objects.")

    _ = get_settings()

    if width <= 0 or height <= 0:
        return _error_result("invalid_chart_spec", "width and height must be greater than zero.")
    if dpi <= 0:
        return _error_result("invalid_chart_spec", "dpi must be greater than zero.")
    if min_dpi <= 0:
        return _error_result("invalid_chart_spec", "min_dpi must be greater than zero.")
    if max_points_per_series <= 0:
        return _error_result("invalid_chart_spec", "max_points_per_series must be greater than zero.")
    if max_label_length is not None and max_label_length <= 4:
        return _error_result("invalid_chart_spec", "max_label_length must be greater than 4.")
    if max_visible_ticks is not None and max_visible_ticks <= 0:
        return _error_result("invalid_chart_spec", "max_visible_ticks must be greater than zero.")
    if label_rotation is not None and label_rotation not in {0, 30, 45, 60, 90}:
        return _error_result("invalid_chart_spec", "label_rotation must be one of: 0, 30, 45, 60, 90.")
    if target_png_bytes <= 8_192:
        return _error_result("invalid_chart_spec", "target_png_bytes must be greater than 8192.")
    if font_size is not None and font_size <= 0:
        return _error_result("invalid_chart_spec", "font_size must be greater than zero.")
    if layout_pad is not None and layout_pad < 0:
        return _error_result("invalid_chart_spec", "layout_pad must be >= 0.")
    for margin_name, margin in (
        ("margin_left", margin_left),
        ("margin_right", margin_right),
        ("margin_top", margin_top),
        ("margin_bottom", margin_bottom),
    ):
        if margin is not None and (margin < 0 or margin > 1):
            return _error_result("invalid_chart_spec", f"{margin_name} must be between 0 and 1.")
    if transparency is not None and (transparency < 0 or transparency > 1):
        return _error_result("invalid_chart_spec", "transparency must be between 0 and 1.")
    try:
        resolved_background_color = _resolve_optional_color(background_color, "background_color")
        resolved_axes_background_color = _resolve_optional_color(axes_background_color, "axes_background_color")
        resolved_text_color = _resolve_optional_color(text_color, "text_color")
        resolved_axis_label_color = _resolve_optional_color(axis_label_color, "axis_label_color")
        resolved_tick_label_color = _resolve_optional_color(tick_label_color, "tick_label_color")
        resolved_series_colors = _parse_series_colors(series_colors)
        resolved_legend_position = _resolve_legend_position(legend_position)
        alpha = float(transparency) if transparency is not None else 1.0
    except ValueError as exc:
        return _error_result("invalid_chart_spec", str(exc))
    _LOGGER.info(
        (
            "chart_request series_count=%s first_type=%s width=%s height=%s dpi=%s "
            "min_dpi=%s max_points_per_series=%s target_png_bytes=%s return_markdown_data_url=%s"
        ),
        len(series),
        _normalize_chart_type((series[0] if isinstance(series[0], dict) else {}).get("chart_type", "line")),
        width,
        height,
        dpi,
        min_dpi,
        max_points_per_series,
        target_png_bytes,
        return_markdown_data_url,
    )

    try:
        rc: dict[str, Any] = {}
        if font_family:
            rc["font.family"] = font_family
        if font_size is not None:
            rc["font.size"] = float(font_size)
        with plt.rc_context(rc):
            fig, ax = plt.subplots(figsize=(float(width), float(height)))
        if resolved_background_color:
            fig.patch.set_facecolor(resolved_background_color)
            fig.patch.set_alpha(alpha)
        if resolved_axes_background_color:
            ax.set_facecolor(resolved_axes_background_color)
            ax.patch.set_alpha(alpha)
        elif resolved_background_color:
            ax.set_facecolor(resolved_background_color)
            ax.patch.set_alpha(alpha)
        plotted = 0
        date_axis_detected = False
        first_entry = series[0] if isinstance(series[0], dict) else {}
        first_chart_type = _normalize_chart_type(first_entry.get("chart_type", "line"))
        if first_chart_type in {"grouped_bar", "stacked_bar", "multi_line"}:
            plotted, date_axis_detected = _render_multi_series(
                ax,
                [item for item in series if isinstance(item, dict)],
                max_points=max_points_per_series,
                chart_type=first_chart_type,
                sort_x=sort_x,
                series_colors=resolved_series_colors,
                transparency=alpha,
            )
        elif first_chart_type == "heatmap":
            matrix, x_labels, y_labels = _extract_heatmap(first_entry)
            if matrix:
                effective_colormap = str(colormap or first_entry.get("colormap") or "viridis")
                im = ax.imshow(matrix, aspect="auto", cmap=effective_colormap, alpha=alpha)
                ax.set_xticks(list(range(len(x_labels))), x_labels, rotation=45, ha="right")
                ax.set_yticks(list(range(len(y_labels))), y_labels)
                fig.colorbar(im, ax=ax)
                plotted = 1
        else:
            for idx, entry in enumerate(series):
                if not isinstance(entry, dict):
                    continue
                rendered, is_date_axis = _render_single_series(
                    ax,
                    idx,
                    entry,
                    max_points=max_points_per_series,
                    sort_x=sort_x,
                    series_colors=resolved_series_colors,
                    transparency=alpha,
                )
                date_axis_detected = date_axis_detected or is_date_axis
                if rendered:
                    plotted += 1

        if plotted == 0:
            plt.close(fig)
            return _error_result("invalid_chart_spec", "No plottable numeric series found.")

        ax.set_title(title or "NERM Chart")
        ax.set_xlabel(x_label or "X")
        ax.set_ylabel(y_label or "Value")
        if resolved_text_color:
            ax.title.set_color(resolved_text_color)
        if resolved_axis_label_color:
            ax.xaxis.label.set_color(resolved_axis_label_color)
            ax.yaxis.label.set_color(resolved_axis_label_color)
        if resolved_tick_label_color:
            ax.tick_params(axis="x", colors=resolved_tick_label_color)
            ax.tick_params(axis="y", colors=resolved_tick_label_color)
            for spine in ax.spines.values():
                spine.set_color(resolved_tick_label_color)
        if plotted > 1 and first_chart_type not in {"pie", "donut"}:
            legend = ax.legend(loc=resolved_legend_position)
            if legend is not None and (resolved_text_color or resolved_axis_label_color):
                legend_color = resolved_text_color or resolved_axis_label_color
                for text_artist in legend.get_texts():
                    text_artist.set_color(legend_color)
        ax.grid(bool(show_grid), alpha=0.25)
        if date_axis_detected:
            import matplotlib.dates as mdates

            locator = mdates.AutoDateLocator(minticks=8, maxticks=20)
            ax.xaxis.set_major_locator(locator)
            ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        _apply_readability_layout(
            fig,
            ax,
            first_chart_type,
            plotted,
            date_axis=date_axis_detected,
            max_label_length=max_label_length,
            max_visible_ticks=max_visible_ticks,
            label_rotation=label_rotation,
        )
        if any(v is not None for v in (margin_left, margin_right, margin_top, margin_bottom)):
            adjust_kwargs: dict[str, float] = {}
            if margin_left is not None:
                adjust_kwargs["left"] = margin_left
            if margin_right is not None:
                adjust_kwargs["right"] = margin_right
            if margin_top is not None:
                adjust_kwargs["top"] = margin_top
            if margin_bottom is not None:
                adjust_kwargs["bottom"] = margin_bottom
            fig.subplots_adjust(**adjust_kwargs)
        else:
            fig.tight_layout(pad=layout_pad if layout_pad is not None else 1.08)

        png_bytes, used_dpi = _encode_png_with_budget(
            fig,
            start_dpi=int(dpi),
            min_dpi=int(min_dpi),
            target_png_bytes=int(target_png_bytes),
        )
        plt.close(fig)
        metadata = {
            "chart_type": first_chart_type,
            "series_count": plotted,
            "title": title or "NERM Chart",
            "x_label": x_label or "X",
            "y_label": y_label or "Value",
            "dpi": used_dpi,
            "png_bytes": len(png_bytes),
            "target_png_bytes": target_png_bytes,
            "sort_x": "auto" if sort_x is None else sort_x,
            "readability": {
                "max_label_length": max_label_length if max_label_length is not None else "auto",
                "max_visible_ticks": max_visible_ticks if max_visible_ticks is not None else "auto",
                "label_rotation": label_rotation if label_rotation is not None else "auto",
            },
        }
        if resolved_background_color:
            metadata["background_color"] = resolved_background_color
        if resolved_axes_background_color:
            metadata["axes_background_color"] = resolved_axes_background_color
        if resolved_text_color:
            metadata["text_color"] = resolved_text_color
        if resolved_axis_label_color:
            metadata["axis_label_color"] = resolved_axis_label_color
        if resolved_tick_label_color:
            metadata["tick_label_color"] = resolved_tick_label_color
        if font_family:
            metadata["font_family"] = font_family
        if font_size is not None:
            metadata["font_size"] = font_size
        metadata["legend_position"] = resolved_legend_position
        if layout_pad is not None:
            metadata["layout_pad"] = layout_pad
        if any(v is not None for v in (margin_left, margin_right, margin_top, margin_bottom)):
            metadata["margins"] = {
                "left": margin_left,
                "right": margin_right,
                "top": margin_top,
                "bottom": margin_bottom,
            }
        if resolved_series_colors:
            metadata["series_colors"] = resolved_series_colors
        if colormap:
            metadata["colormap"] = colormap
        metadata["transparency"] = alpha
        encoded = base64.b64encode(png_bytes).decode("ascii")
        if return_markdown_data_url:
            metadata["markdown"] = f"![NERM chart](data:image/png;base64,{encoded})"
        if len(png_bytes) > target_png_bytes:
            metadata["size_warning"] = (
                "Chart exceeded target size after downscaling; returning image anyway."
            )
        _LOGGER.info(
            (
                "chart_result chart_type=%s series_count=%s png_bytes=%s dpi=%s "
                "size_warning=%s markdown_fallback=%s"
            ),
            metadata.get("chart_type"),
            metadata.get("series_count"),
            metadata.get("png_bytes"),
            metadata.get("dpi"),
            "size_warning" in metadata,
            "markdown" in metadata,
        )
        text_payload = {
            "status": "success",
            "tool": "nerm_generate_chart",
            "chart_type": first_chart_type,
            "series_count": plotted,
            "png_bytes": len(png_bytes),
        }
        return CallToolResult(
            content=[
                TextContent(type="text", text=json.dumps(text_payload, default=str)),
                ImageContent(type="image", mimeType="image/png", data=encoded),
            ],
            structuredContent=metadata,
            isError=False,
        )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.exception("chart_generation_failed error=%s", exc)
        return _error_result("chart_generation_error", f"Failed to render chart: {exc}")


nerm_generate_chart.__doc__ = append_tool_guidance(nerm_generate_chart.__doc__, CHART_USAGE)
