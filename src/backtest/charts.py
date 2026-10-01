"""Portable dependency-free SVG charts for generated reports."""

import html

import numpy as np

COLORS = ["#2563eb", "#0d9488", "#d97706", "#9333ea", "#64748b"]


def svg_plot(
    series,
    title,
    xlabel,
    ylabel,
    *,
    kind="line",
    x_percent=False,
    y_percent=False,
    benchmark=None,
):
    series = [(str(label), list(points)) for label, points in series]
    finite = [
        (float(x), float(y))
        for _, points in series
        for x, y in points
        if np.isfinite(x) and np.isfinite(y)
    ]
    if not finite:
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 180"><text x="32" y="80">Không đủ dữ liệu hữu hạn để vẽ.</text></svg>'
    xs, ys = zip(*finite)
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    if benchmark is not None and np.isfinite(benchmark):
        ymin, ymax = min(ymin, benchmark), max(ymax, benchmark)
    if kind in ("bar", "area"):
        ymin, ymax = min(0.0, ymin), max(0.0, ymax)
    x_range = xmax - xmin
    y_range = ymax - ymin
    if x_range == 0:
        xmin -= 0.5
        xmax += 0.5
    elif kind != "bar":
        xmin -= x_range * 0.03
        xmax += x_range * 0.03
    padding = y_range * 0.12 if y_range else max(abs(ymax) * 0.1, 0.001)
    ymin -= padding
    ymax += padding
    legend_y = 428
    height = legend_y + 30 * len(series) + (32 if benchmark is not None else 0) + 20
    left, right, top, bottom = 95, 920, 82, 342

    def scale_x(value):
        return left + (value - xmin) / (xmax - xmin) * (right - left)

    def scale_y(value):
        return bottom - (value - ymin) / (ymax - ymin) * (bottom - top)

    def format_value(value, percent=False):
        return f"{100 * value:.2f}%" if percent else f"{value:.4g}"

    escape = html.escape
    output = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 {height}" role="img" aria-label="{escape(title)}">',
        f'<rect width="960" height="{height}" rx="16" fill="white"/>',
        '<g font-family="Arial, sans-serif" fill="#172b4d" font-size="14">',
        f'<text x="32" y="34" font-size="19" font-weight="bold">{escape(title)}</text>',
        f'<text x="95" y="65" fill="#52637a">{escape(ylabel)}</text>',
    ]
    for value in np.linspace(ymin, ymax, 5):
        y = scale_y(value)
        output.append(
            f'<path d="M{left} {y}H{right}" stroke="#e6edf5"/>'
            f'<text x="82" y="{y + 5}" text-anchor="end">{format_value(value, y_percent)}</text>'
        )
    if ymin <= 0 <= ymax:
        output.append(f'<path d="M{left} {scale_y(0)}H{right}" stroke="#94a3b8"/>')
    if kind == "bar":
        categories = sorted(set(xs))
        group_width = (right - left) / len(categories)
        bar_width = min(52, group_width * 0.72 / max(len(series), 1))
        for group_index, x in enumerate(categories):
            center = left + (group_index + 0.5) * group_width
            output.append(
                f'<text x="{center}" y="372" text-anchor="middle">{format_value(x, x_percent)}</text>'
            )
            for series_index, (label, points) in enumerate(series):
                y = dict(points).get(x, float("nan"))
                if not np.isfinite(y):
                    continue
                bar_x = center + (series_index - len(series) / 2) * bar_width
                plot_y = min(scale_y(y), scale_y(0))
                bar_height = abs(scale_y(y) - scale_y(0))
                output.append(
                    f'<rect x="{bar_x + 2}" y="{plot_y}" width="{bar_width - 4}" '
                    f'height="{bar_height}" rx="3" fill="{COLORS[series_index % len(COLORS)]}">'
                    f'<title>{escape(label)}: {y:.4f}</title></rect>'
                )
    else:
        for x in np.linspace(min(xs), max(xs), 5):
            output.append(
                f'<text x="{scale_x(x)}" y="372" text-anchor="middle">{format_value(x, x_percent)}</text>'
            )
        for series_index, (label, points) in enumerate(series):
            color = COLORS[series_index % len(COLORS)]
            segment = []
            for x, y in points + [(0, float("nan"))]:
                if np.isfinite(x) and np.isfinite(y):
                    segment.append((x, y))
                elif segment:
                    coordinates = " ".join(
                        f"{scale_x(a):.2f},{scale_y(b):.2f}" for a, b in segment
                    )
                    if kind == "area":
                        output.append(
                            f'<polygon points="{scale_x(segment[0][0])},{scale_y(0)} '
                            f'{coordinates} {scale_x(segment[-1][0])},{scale_y(0)}" '
                            f'fill="{color}" fill-opacity="0.13"/>'
                        )
                    output.append(
                        f'<polyline points="{coordinates}" fill="none" stroke="{color}" '
                        'stroke-width="2.6" stroke-linejoin="round"/>'
                    )
                    if len(segment) == 1 or kind == "frontier":
                        radius = 6 if len(segment) == 1 else 2.4
                        for a, b in segment:
                            output.append(
                                f'<circle cx="{scale_x(a)}" cy="{scale_y(b)}" r="{radius}" '
                                f'fill="{color}" stroke="white" stroke-width="1">'
                                f'<title>{escape(label)}: {format_value(a, x_percent)}, '
                                f'{format_value(b, y_percent)}</title></circle>'
                            )
                    segment = []
    if benchmark is not None and np.isfinite(benchmark):
        output.append(
            f'<path d="M{left} {scale_y(benchmark)}H{right}" stroke="#64748b" '
            'stroke-width="2" stroke-dasharray="7 5"/>'
        )
    output.append(
        f'<text x="510" y="404" text-anchor="middle" fill="#52637a">{escape(xlabel)}</text>'
    )
    labels = [(name, COLORS[index % len(COLORS)]) for index, (name, _) in enumerate(series)]
    if benchmark is not None:
        labels.append(("Benchmark (đường nét đứt)", "#64748b"))
    for index, (name, color) in enumerate(labels):
        y = legend_y + index * 30
        output.append(
            f'<rect x="95" y="{y - 10}" width="20" height="10" rx="3" fill="{color}"/>'
            f'<text x="128" y="{y}">{escape(name)}</text>'
        )
    output.append("</g></svg>")
    return "".join(output)


def allocation_chart(weights):
    assets = list(weights.index)
    height = 130 + 70 * len(weights.columns) + 28 * len(assets)
    output = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 {height}" role="img" aria-label="Tỷ trọng danh mục">',
        f'<rect width="960" height="{height}" fill="white"/><g font-family="Arial" font-size="15" fill="#172b4d">',
        '<text x="30" y="34" font-size="20" font-weight="bold">Tỷ trọng tại cửa sổ huấn luyện đầu tiên</text>',
    ]
    for column_index, name in enumerate(weights.columns):
        y = 65 + column_index * 70
        output.append(f'<text x="30" y="{y + 27}">{html.escape(str(name))}</text>')
        offset = 0
        for asset_index, asset in enumerate(assets):
            weight = float(weights.loc[asset, name])
            width = 700 * weight
            color = COLORS[asset_index % len(COLORS)]
            if width > 0:
                output.append(
                    f'<rect x="{200 + offset}" y="{y}" width="{width}" height="40" fill="{color}">'
                    f'<title>{html.escape(str(asset))}: {weight:.2%}</title></rect>'
                )
                if width > 55:
                    output.append(
                        f'<text x="{200 + offset + width / 2}" y="{y + 26}" '
                        f'text-anchor="middle" fill="white" font-weight="bold">{weight:.1%}</text>'
                    )
            offset += width
    y = 85 + 70 * len(weights.columns)
    output.append(
        f'<text x="200" y="{y}" fill="#52637a">Mỗi thanh = 100% vốn · Di chuột vào từng phần để xem tỷ trọng</text>'
    )
    for asset_index, asset in enumerate(assets):
        item_y = y + 35 + asset_index * 28
        output.append(
            f'<rect x="200" y="{item_y - 12}" width="18" height="12" '
            f'fill="{COLORS[asset_index % len(COLORS)]}"/>'
            f'<text x="230" y="{item_y}">{html.escape(str(asset))}</text>'
        )
    return "".join(output) + "</g></svg>"


def monthly_heatmap(returns_by_strategy):
    rows = []
    for name, series in returns_by_strategy.items():
        for year in sorted(set(series.index.year)):
            rows.append(
                (name, year, {date.month: float(value) for date, value in series.items() if date.year == year})
            )
    values = [abs(value) for _, _, row in rows for value in row.values() if np.isfinite(value)]
    bound = max(values or [0.01]) or 0.01
    height = 135 + 36 * len(rows)
    output = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 {height}" role="img" aria-label="Bản đồ nhiệt lợi suất tháng">',
        f'<rect width="1100" height="{height}" fill="white"/><g font-family="Arial" font-size="13" fill="#172b4d">',
        '<text x="24" y="30" font-size="19" font-weight="bold">Lợi suất ròng từng tháng (%)</text>',
        '<text x="24" y="55" fill="#52637a">Đỏ: âm · Xanh: dương · Ô xám: ngoài kỳ đánh giá</text>',
    ]
    for month in range(1, 13):
        output.append(f'<text x="{228 + (month - 1) * 70}" y="83" text-anchor="middle">T{month:02d}</text>')
    for row_index, (name, year, row) in enumerate(rows):
        y = 96 + row_index * 36
        output.append(f'<text x="24" y="{y + 20}">{html.escape(name)} · {year}</text>')
        for month in range(1, 13):
            value = row.get(month, float("nan"))
            if np.isfinite(value):
                intensity = min(abs(value) / bound, 1)
                target = (15, 118, 110) if value >= 0 else (190, 55, 65)
                rgb = tuple(round(248 + (component - 248) * intensity) for component in target)
                fill = "#%02x%02x%02x" % rgb
                label = f"{100 * value:+.1f}"
                ink = "white" if intensity > 0.65 else "#172b4d"
            else:
                fill, label, ink = "#edf1f5", "—", "#8b97a8"
            x = 194 + (month - 1) * 70
            output.append(
                f'<rect x="{x}" y="{y}" width="67" height="31" rx="4" fill="{fill}"/>'
                f'<text x="{x + 33}" y="{y + 20}" text-anchor="middle" fill="{ink}">{label}</text>'
            )
    output.append(
        f'<text x="24" y="{height - 12}" fill="#52637a">Thang màu đối xứng: '
        f'−{100 * bound:.1f}% đến +{100 * bound:.1f}%</text>'
    )
    return "".join(output) + "</g></svg>"
