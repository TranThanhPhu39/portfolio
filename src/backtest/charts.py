"""Portable SVG charts with readable axes and separated legends."""
import html
import numpy as np

COLORS = ['#2563eb', '#0d9488', '#d97706', '#9333ea', '#64748b']


def svg_plot(series, title, xlabel, ylabel, *, kind='line', x_percent=False, y_percent=False, benchmark=None):
    series = [(str(label), list(points)) for label, points in series]
    finite = [(float(x), float(y)) for _, points in series for x, y in points if np.isfinite(x) and np.isfinite(y)]
    if not finite:
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 180"><text x="32" y="80">Không đủ dữ liệu hữu hạn để vẽ.</text></svg>'
    xs, ys = zip(*finite)
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    if benchmark is not None and np.isfinite(benchmark):
        ymin, ymax = min(ymin, benchmark), max(ymax, benchmark)
    if kind in ('bar', 'area'):
        ymin, ymax = min(0., ymin), max(0., ymax)
    xr = xmax-xmin
    yr = ymax-ymin
    if xr == 0: xmin -= .5; xmax += .5
    elif kind != 'bar': xmin -= xr*.03; xmax += xr*.03
    pad = yr*.12 if yr else max(abs(ymax)*.1, .001)
    ymin -= pad; ymax += pad
    legend_y = 428
    height = legend_y + 30*len(series) + (32 if benchmark is not None else 0) + 20
    left, right, top, bottom = 95, 920, 82, 342
    sx = lambda x: left+(x-xmin)/(xmax-xmin)*(right-left)
    sy = lambda y: bottom-(y-ymin)/(ymax-ymin)*(bottom-top)
    def fmt(v, percent=False):
        return f'{100*v:.2f}%' if percent else f'{v:.4g}'
    esc = html.escape
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 {height}" role="img" aria-label="{esc(title)}">',
           f'<rect width="960" height="{height}" rx="16" fill="white"/>',
           '<g font-family="Arial, sans-serif" fill="#172b4d" font-size="14">',
           f'<text x="32" y="34" font-size="19" font-weight="bold">{esc(title)}</text>',
           f'<text x="95" y="65" fill="#52637a">{esc(ylabel)}</text>']
    for v in np.linspace(ymin,ymax,5):
        y=sy(v)
        out.append(f'<path d="M{left} {y}H{right}" stroke="#e6edf5"/><text x="82" y="{y+5}" text-anchor="end">{fmt(v,y_percent)}</text>')
    if ymin <= 0 <= ymax:
        out.append(f'<path d="M{left} {sy(0)}H{right}" stroke="#94a3b8"/>')
    if kind == 'bar':
        categories = sorted(set(xs))
        group_width = (right-left)/len(categories)
        bw = min(52,group_width*.72/max(len(series),1))
        for j,x in enumerate(categories):
            center=left+(j+.5)*group_width
            out.append(f'<text x="{center}" y="372" text-anchor="middle">{fmt(x,x_percent)}</text>')
            for i,(label,points) in enumerate(series):
                y=dict(points).get(x,float('nan'))
                if not np.isfinite(y): continue
                bx=center+(i-len(series)/2)*bw
                py=min(sy(y),sy(0)); bh=abs(sy(y)-sy(0))
                out.append(f'<rect x="{bx+2}" y="{py}" width="{bw-4}" height="{bh}" rx="3" fill="{COLORS[i%len(COLORS)]}"><title>{esc(label)}: {y:.4f}</title></rect>')
    else:
        for x in np.linspace(min(xs),max(xs),5):
            out.append(f'<text x="{sx(x)}" y="372" text-anchor="middle">{fmt(x,x_percent)}</text>')
        for i,(label,points) in enumerate(series):
            color=COLORS[i%len(COLORS)]
            segment=[]
            for x,y in points+[(0,float('nan'))]:
                if np.isfinite(x) and np.isfinite(y): segment.append((x,y))
                elif segment:
                    coords=' '.join(f'{sx(a):.2f},{sy(b):.2f}' for a,b in segment)
                    if kind=='area':
                        out.append(f'<polygon points="{sx(segment[0][0])},{sy(0)} {coords} {sx(segment[-1][0])},{sy(0)}" fill="{color}" fill-opacity="0.13"/>')
                    out.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2.6" stroke-linejoin="round"/>')
                    if len(segment)==1 or kind=='frontier':
                        radius=6 if len(segment)==1 else 2.4
                        for a,b in segment:
                            out.append(f'<circle cx="{sx(a)}" cy="{sy(b)}" r="{radius}" fill="{color}" stroke="white" stroke-width="1"><title>{esc(label)}: {fmt(a,x_percent)}, {fmt(b,y_percent)}</title></circle>')
                    segment=[]
    if benchmark is not None and np.isfinite(benchmark):
        out.append(f'<path d="M{left} {sy(benchmark)}H{right}" stroke="#64748b" stroke-width="2" stroke-dasharray="7 5"/>')
    out.append(f'<text x="510" y="404" text-anchor="middle" fill="#52637a">{esc(xlabel)}</text>')
    labels=[(name,COLORS[i%len(COLORS)]) for i,(name,_) in enumerate(series)]
    if benchmark is not None: labels.append(('Benchmark (đường nét đứt)','#64748b'))
    for i,(name,color) in enumerate(labels):
        y=legend_y+i*30
        out.append(f'<rect x="95" y="{y-10}" width="20" height="10" rx="3" fill="{color}"/><text x="128" y="{y}">{esc(name)}</text>')
    out.append('</g></svg>')
    return ''.join(out)


def allocation_chart(weights):
    """100% stacked horizontal bars for first-window asset allocations."""
    assets=list(weights.index)
    height=130+70*len(weights.columns)+28*len(assets)
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 {height}" role="img" aria-label="Tỷ trọng danh mục"><rect width="960" height="{height}" fill="white"/><g font-family="Arial" font-size="15" fill="#172b4d">',
         '<text x="30" y="34" font-size="20" font-weight="bold">Tỷ trọng tại cửa sổ huấn luyện đầu tiên</text>']
    for j,name in enumerate(weights.columns):
        y=65+j*70
        out.append(f'<text x="30" y="{y+27}">{html.escape(str(name))}</text>')
        offset=0
        for i,asset in enumerate(assets):
            w=float(weights.loc[asset,name]); width=700*w; color=COLORS[i%len(COLORS)]
            if width>0:
                out.append(f'<rect x="{200+offset}" y="{y}" width="{width}" height="40" fill="{color}"><title>{html.escape(str(asset))}: {w:.2%}</title></rect>')
                if width>55: out.append(f'<text x="{200+offset+width/2}" y="{y+26}" text-anchor="middle" fill="white" font-weight="bold">{w:.1%}</text>')
            offset+=width
    y=85+70*len(weights.columns)
    out.append(f'<text x="200" y="{y}" fill="#52637a">Mỗi thanh = 100% vốn · Di chuột vào từng phần để xem tỷ trọng</text>')
    for i,asset in enumerate(assets):
        py=y+35+i*28
        out.append(f'<rect x="200" y="{py-12}" width="18" height="12" fill="{COLORS[i%len(COLORS)]}"/><text x="230" y="{py}">{html.escape(str(asset))}</text>')
    return ''.join(out)+'</g></svg>'


def monthly_heatmap(returns_by_strategy):
    """Shared symmetric color scale, explicit missing calendar months."""
    rows=[]
    for name,series in returns_by_strategy.items():
        for year in sorted(set(series.index.year)):
            rows.append((name,year,{d.month:float(v) for d,v in series.items() if d.year==year}))
    values=[abs(v) for _,_,row in rows for v in row.values() if np.isfinite(v)]
    bound=max(values or [0.01]) or .01
    height=135+36*len(rows)
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 {height}" role="img" aria-label="Bản đồ nhiệt lợi suất tháng"><rect width="1100" height="{height}" fill="white"/><g font-family="Arial" font-size="13" fill="#172b4d">',
         '<text x="24" y="30" font-size="19" font-weight="bold">Lợi suất ròng từng tháng (%)</text>',
         '<text x="24" y="55" fill="#52637a">Đỏ: âm · Xanh: dương · Ô xám: ngoài kỳ đánh giá · Các chiến lược dùng chung thang màu</text>']
    for month in range(1,13):
        out.append(f'<text x="{228+(month-1)*70}" y="83" text-anchor="middle">T{month:02d}</text>')
    for k,(name,year,row) in enumerate(rows):
        y=96+k*36
        out.append(f'<text x="24" y="{y+20}">{html.escape(name)} · {year}</text>')
        for month in range(1,13):
            value=row.get(month,float('nan'))
            if np.isfinite(value):
                t=min(abs(value)/bound,1)
                target=(15,118,110) if value>=0 else (190,55,65)
                rgb=tuple(round(248+(component-248)*t) for component in target)
                fill='#%02x%02x%02x'%rgb; label=f'{100*value:+.1f}'; ink='white' if t>.65 else '#172b4d'
            else: fill='#edf1f5'; label='—'; ink='#8b97a8'
            x=194+(month-1)*70
            out.append(f'<rect x="{x}" y="{y}" width="67" height="31" rx="4" fill="{fill}"/><text x="{x+33}" y="{y+20}" text-anchor="middle" fill="{ink}">{label}</text>')
    out.append(f'<text x="24" y="{height-12}" fill="#52637a">Thang màu đối xứng: −{100*bound:.1f}% đến +{100*bound:.1f}% · Số trong ô đã làm tròn</text>')
    return ''.join(out)+'</g></svg>'
