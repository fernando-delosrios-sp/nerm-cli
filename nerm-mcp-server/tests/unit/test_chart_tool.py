from nerm.tools.charts import _sort_xy_if_date_based, nerm_generate_chart


def _dump(result):
    return result.model_dump(mode="json")


def test_generate_chart_returns_image_block_plus_metadata() -> None:
    result = nerm_generate_chart(
        [{"label": "Profiles", "points": [{"x": "Jan", "y": 10}, {"x": "Feb", "y": 14}]}],
        embed_in_response=True,
    )
    result = _dump(result)
    assert result["isError"] is False
    assert isinstance(result["content"], list)
    assert result["content"][0]["type"] == "text"
    assert isinstance(result["content"][0]["text"], str)
    metadata = result["structuredContent"]
    assert metadata["title"] == "NERM Chart"
    assert isinstance(metadata["png_bytes"], int)
    assert metadata["sort_x"] == "auto"
    assert metadata["readability"]["max_label_length"] == "auto"
    assert result["content"][1]["type"] == "image"
    assert result["content"][1]["mimeType"] == "image/png"
    assert isinstance(result["content"][1]["data"], str)


def test_generate_chart_compat_args_do_not_change_delivery_mode() -> None:
    result = nerm_generate_chart(
        [{"label": "Profiles", "values": [1, 2, 3]}],
        embed_in_response=False,
        include_base64=True,
    )
    result = _dump(result)
    assert result["isError"] is False
    assert result["content"][0]["type"] == "text"
    assert result["content"][1]["type"] == "image"


def test_generate_chart_supports_pie_chart() -> None:
    result = nerm_generate_chart(
        [
            {
                "chart_type": "pie",
                "x": ["High", "Medium", "Low"],
                "y": [12, 19, 7],
            }
        ]
    )
    result = _dump(result)
    assert result["isError"] is False
    metadata = result["structuredContent"]
    assert metadata["chart_type"] == "pie"


def test_generate_chart_accepts_chart_type_aliases() -> None:
    result = nerm_generate_chart(
        [
            {
                "chart_type": "pie chart",
                "x": ["High", "Medium", "Low"],
                "y": [12, 19, 7],
            }
        ]
    )
    result = _dump(result)
    assert result["isError"] is False
    metadata = result["structuredContent"]
    assert metadata["chart_type"] == "pie"


def test_generate_chart_unknown_type_falls_back_to_line() -> None:
    result = nerm_generate_chart(
        [
            {
                "chart_type": "unknown_type",
                "x": ["Jan", "Feb", "Mar"],
                "y": [10, 14, 20],
            }
        ]
    )
    result = _dump(result)
    assert result["isError"] is False
    metadata = result["structuredContent"]
    assert metadata["chart_type"] == "line"


def test_generate_chart_can_emit_markdown_data_url_fallback() -> None:
    result = nerm_generate_chart(
        [
            {
                "chart_type": "pie",
                "x": ["High", "Medium", "Low"],
                "y": [12, 19, 7],
            }
        ],
        return_markdown_data_url=True,
    )
    result = _dump(result)
    assert result["isError"] is False
    metadata = result["structuredContent"]
    assert metadata["chart_type"] == "pie"
    assert metadata["markdown"].startswith("![NERM chart](data:image/png;base64,")


def test_generate_chart_supports_donut_chart() -> None:
    result = nerm_generate_chart(
        [
            {
                "chart_type": "donut",
                "x": ["High", "Medium", "Low"],
                "y": [12, 19, 7],
            }
        ]
    )
    result = _dump(result)
    assert result["isError"] is False
    assert result["structuredContent"]["chart_type"] == "donut"


def test_generate_chart_supports_scatter_chart() -> None:
    result = nerm_generate_chart(
        [
            {
                "chart_type": "scatter",
                "points": [[1, 10], [2, 14], [3, 20]],
            }
        ]
    )
    result = _dump(result)
    assert result["isError"] is False
    assert result["structuredContent"]["chart_type"] == "scatter"


def test_generate_chart_supports_area_chart() -> None:
    result = nerm_generate_chart(
        [
            {
                "chart_type": "area",
                "x": ["Jan", "Feb", "Mar"],
                "y": [10, 14, 20],
            }
        ]
    )
    result = _dump(result)
    assert result["isError"] is False
    assert result["structuredContent"]["chart_type"] == "area"


def test_generate_chart_supports_horizontal_bar_chart() -> None:
    result = nerm_generate_chart(
        [
            {
                "chart_type": "horizontal_bar",
                "x": ["A", "B", "C"],
                "y": [3, 7, 5],
            }
        ]
    )
    result = _dump(result)
    assert result["isError"] is False
    assert result["structuredContent"]["chart_type"] == "horizontal_bar"


def test_generate_chart_supports_histogram_chart() -> None:
    result = nerm_generate_chart(
        [
            {
                "chart_type": "histogram",
                "values": [1, 1, 2, 3, 5, 8, 13, 21],
            }
        ]
    )
    result = _dump(result)
    assert result["isError"] is False
    assert result["structuredContent"]["chart_type"] == "histogram"


def test_generate_chart_supports_box_chart() -> None:
    result = nerm_generate_chart(
        [
            {
                "chart_type": "box",
                "values": [1, 2, 2, 3, 5, 8, 13],
            }
        ]
    )
    result = _dump(result)
    assert result["isError"] is False
    assert result["structuredContent"]["chart_type"] == "box"


def test_generate_chart_supports_grouped_bar_chart() -> None:
    result = nerm_generate_chart(
        [
            {"chart_type": "grouped_bar", "label": "A", "x": ["Q1", "Q2"], "y": [10, 15]},
            {"chart_type": "grouped_bar", "label": "B", "x": ["Q1", "Q2"], "y": [12, 14]},
        ]
    )
    result = _dump(result)
    assert result["isError"] is False
    assert result["structuredContent"]["chart_type"] == "grouped_bar"


def test_generate_chart_supports_stacked_bar_chart() -> None:
    result = nerm_generate_chart(
        [
            {"chart_type": "stacked_bar", "label": "A", "x": ["Q1", "Q2"], "y": [10, 15]},
            {"chart_type": "stacked_bar", "label": "B", "x": ["Q1", "Q2"], "y": [12, 14]},
        ]
    )
    result = _dump(result)
    assert result["isError"] is False
    assert result["structuredContent"]["chart_type"] == "stacked_bar"


def test_generate_chart_supports_multi_line_chart() -> None:
    result = nerm_generate_chart(
        [
            {"chart_type": "multi_line", "label": "A", "x": ["Q1", "Q2"], "y": [10, 15]},
            {"chart_type": "multi_line", "label": "B", "x": ["Q1", "Q2"], "y": [12, 14]},
        ]
    )
    result = _dump(result)
    assert result["isError"] is False
    assert result["structuredContent"]["chart_type"] == "multi_line"


def test_generate_chart_supports_heatmap_chart() -> None:
    result = nerm_generate_chart(
        [
            {
                "chart_type": "heatmap",
                "matrix": [[1, 2, 3], [4, 5, 6]],
                "x_labels": ["A", "B", "C"],
                "y_labels": ["Row1", "Row2"],
            }
        ]
    )
    result = _dump(result)
    assert result["isError"] is False
    assert result["structuredContent"]["chart_type"] == "heatmap"


def test_generate_chart_rejects_unplottable_series() -> None:
    result = nerm_generate_chart([{"label": "Broken", "points": [{"x": "Jan", "y": "abc"}]}])
    result = _dump(result)
    assert result["isError"] is True
    assert result["structuredContent"]["error"] == "invalid_chart_spec"


def test_generate_chart_rejects_empty_series() -> None:
    result = nerm_generate_chart([])
    result = _dump(result)
    assert result["isError"] is True
    assert result["structuredContent"]["error"] == "invalid_chart_spec"


def test_generate_chart_returns_warning_not_error_when_oversized() -> None:
    result = nerm_generate_chart(
        [{"label": "Profiles", "values": list(range(5000))}],
        width=16,
        height=9,
        dpi=300,
        min_dpi=300,
        target_png_bytes=9_000,
    )
    result = _dump(result)
    assert result["isError"] is False
    metadata = result["structuredContent"]
    assert "size_warning" in metadata


def test_generate_chart_emits_trace_logs(caplog) -> None:
    with caplog.at_level("DEBUG", logger="nerm.tools.charts"):
        result = nerm_generate_chart(
            [{"chart_type": "pie", "x": ["A", "B"], "y": [1, 2]}],
            return_markdown_data_url=True,
        )
    result = _dump(result)
    assert result["isError"] is False
    assert "chart_request series_count=1" in caplog.text
    assert "chart_result chart_type=pie" in caplog.text


def test_generate_chart_result_is_json_serializable() -> None:
    result = nerm_generate_chart([{"chart_type": "line", "values": [1, 2, 3]}])
    _dump(result)


def test_generate_chart_accepts_explicit_readability_controls() -> None:
    result = nerm_generate_chart(
        [{"chart_type": "bar", "x": [f"Category-{i}" for i in range(20)], "y": list(range(20))}],
        max_label_length=20,
        max_visible_ticks=10,
        label_rotation=45,
    )
    result = _dump(result)
    assert result["isError"] is False
    metadata = result["structuredContent"]
    assert metadata["readability"]["max_label_length"] == 20
    assert metadata["readability"]["max_visible_ticks"] == 10
    assert metadata["readability"]["label_rotation"] == 45


def test_generate_chart_rejects_invalid_label_rotation() -> None:
    result = nerm_generate_chart(
        [{"chart_type": "line", "values": [1, 2, 3]}],
        label_rotation=15,
    )
    result = _dump(result)
    assert result["isError"] is True
    assert result["structuredContent"]["error"] == "invalid_chart_spec"


def test_sort_xy_if_date_based_sorts_iso_dates() -> None:
    x_vals = ["2026-03", "2025-12", "2026-01"]
    y_vals = [3.0, 1.0, 2.0]
    sorted_x, sorted_y, did_sort = _sort_xy_if_date_based(x_vals, y_vals, sort_x=None)
    assert did_sort is True
    assert sorted_x == ["2025-12", "2026-01", "2026-03"]
    assert sorted_y == [1.0, 2.0, 3.0]


def test_sort_xy_if_date_based_skips_non_date_labels() -> None:
    x_vals = ["Jan", "Feb", "Mar"]
    y_vals = [1.0, 2.0, 3.0]
    sorted_x, sorted_y, did_sort = _sort_xy_if_date_based(x_vals, y_vals, sort_x=None)
    assert did_sort is False
    assert sorted_x == x_vals
    assert sorted_y == y_vals


def test_sort_xy_respects_sort_x_false() -> None:
    x_vals = ["2026-03", "2025-12", "2026-01"]
    y_vals = [3.0, 1.0, 2.0]
    sorted_x, sorted_y, did_sort = _sort_xy_if_date_based(x_vals, y_vals, sort_x=False)
    assert did_sort is False
    assert sorted_x == x_vals
    assert sorted_y == y_vals


def test_sort_xy_force_true_sorts_non_dates_lexicographically() -> None:
    x_vals = ["Mar", "Jan", "Feb"]
    y_vals = [3.0, 1.0, 2.0]
    sorted_x, sorted_y, did_sort = _sort_xy_if_date_based(x_vals, y_vals, sort_x=True)
    assert did_sort is True
    assert sorted_x == ["Feb", "Jan", "Mar"]
    assert sorted_y == [2.0, 1.0, 3.0]

