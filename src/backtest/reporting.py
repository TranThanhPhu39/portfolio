"""Readable standalone report; calculations and CSV outputs remain unchanged."""
import html
import numpy as np
import pandas as pd


def export_report(out, outputs, table, benchmark, cfg):
    from .charts import svg_plot, allocation_chart, monthly_heatmap
    esc=html.escape
    # Dynamic runs must not inherit the legacy fixed-universe research label.
    def card(title,description,body):
        return f'<section class="card"><h2>{esc(title)}</h2><p class="muted">{esc(description)}</p>{body}</section>'
    first=next(iter(next(iter(outputs.values())).values()))
    dates=first.periods.index
    status='DỮ LIỆU GIẢ LẬP · KHÔNG DÙNG LÀM KẾT QUẢ NGHIÊN CỨU' if cfg['synthetic'] else 'KẾT QUẢ BACKTEST · TẬP CỔ PHIẾU CỐ ĐỊNH'
    intro=f'<header><span class="badge">{status}</span><div class="version">V5.1 · ĐÃ BỔ SUNG SO SÁNH SHARPE TỪNG MÃ</div><h1>Hiệu quả danh mục đầu tư</h1><p>Từ phân bổ danh mục đến hiệu quả sau chi phí giao dịch.</p></header>'
    intro+=f'<div class="stats"><div><span>Chiến lược</span><strong>{len(outputs)}</strong></div><div><span>Tháng ngoài mẫu</span><strong>{len(dates)}</strong></div><div><span>Kịch bản phí</span><strong>{len(cfg["rates"])}</strong></div></div>'
    intro+='<nav><a href="#comparison">So sánh chi phí</a><a href="#details">Diễn biến danh mục</a><a href="#data">Bảng số liệu</a></nav>'
    if cfg.get('universe_mode') == 'dynamic':
        intro='<header><h1>VN100 theo kỳ — chạy thử theo dữ liệu nhóm</h1><p>CHƯA NGHIỆM THU NGHIÊN CỨU. Còn chênh lệch giá/lợi suất và giả định RF.</p><p>'+esc('Lợi suất: '+cfg['return_basis']+'; RF: '+cfg['rf_basis']+'; cuối mẫu: '+cfg['end'])+'</p></header>'
    sections=[intro]
    assumptions='<div class="notes"><div><h3>Dữ liệu và phạm vi</h3><p>'+esc(cfg['universe_selection'])+'</p></div><div><h3>Thời điểm giao dịch</h3><p>'+esc(cfg['execution_assumption'])+'</p></div><div><h3>Quy ước chi phí</h3><p>Vốn đầu = 1. Phí trên từng chiều mua/bán; có phí mua ban đầu, chưa tính thanh lý cuối mẫu.</p></div></div>'
    sections.append(card('Cách đọc báo cáo','Các giả định được giữ nguyên như lần chạy tính toán.',assumptions))
    comparison_file=out/'05_sharpe_assets_comparison.csv'
    if comparison_file.exists():
        detail=pd.read_csv(comparison_file)
        visible=detail[['name','sharpe_annualized','mean_excess_monthly','excess_sd_monthly','months']].copy()
        for column in ['sharpe_annualized','mean_excess_monthly','excess_sd_monthly']:
            visible[column]=visible[column].map(lambda x:f'{x:.6f}' if np.isfinite(x) else '—')
        visible=visible.rename(columns={'name':'Danh mục / mã','sharpe_annualized':'Sharpe năm',
            'mean_excess_monthly':'Lợi suất vượt RF TB tháng','excess_sd_monthly':'SD mẫu lợi suất vượt RF', 'months':'Số tháng'})
        description=(f"Cùng kỳ {detail.start_date.iloc[0]} đến {detail.end_date.iloc[0]}, "
            f"{int(detail.months.iloc[0])} tháng; cùng chuỗi RF theo tháng; chưa trừ phí. "
            "MaxSharpe dùng trọng số mục tiêu của cửa sổ huấn luyện đầu tiên. Đây là so sánh trong mẫu.")
        notes='<p class="caption">MeanAssetSharpe là trung bình cộng Sharpe của tất cả mã, không phải Sharpe của danh mục chia đều. Công thức: √12 × trung bình(r − RF) / độ lệch chuẩn mẫu(r − RF). Bảng dùng SD thực tế, không cộng ridge; vì vậy có thể khác chỉ tiêu mục tiêu của optimizer. Không ép MaxSharpe lớn hơn các mã hoặc lớn hơn trung bình.</p>'
        sections.append(card('05 · Sharpe từng mã và danh mục MaxSharpe',description,
            '<div class="table-wrap">'+visible.to_html(index=False,border=0)+'</div>'+notes))
    weight_file=out/'03_weights.csv'
    if weight_file.exists():
        svg=allocation_chart(pd.read_csv(weight_file,index_col=0))
        (out/'allocation.svg').write_text(svg,encoding='utf-8')
        sections.append(card('01 · Tiền được phân bổ vào đâu?', 'Thanh ngang xếp chồng: mỗi màu là một mã, tổng mỗi thanh bằng 100%. Đây là trọng số đầu tiên, không phải trọng số cố định cho toàn bộ backtest.',svg))
    frontier_path=out/'04_frontier.svg'
    if frontier_path.exists():
        sections.append(card('Rủi ro và lợi suất kỳ vọng','Đường biên hiệu quả và các danh mục tại cửa sổ huấn luyện đầu tiên. Hai trục hiển thị theo phần trăm tháng.',frontier_path.read_text(encoding='utf-8')))
    sharpes=[]
    for name in outputs:
        rows=table[(table.strategy==name)&(table.name=='strategy')].sort_values('transaction_cost_rate')
        sharpes.append((name,list(zip(rows.transaction_cost_rate,rows.sharpe))))
    bs=float(table.loc[table.name=='benchmark','sharpe'].iloc[0])
    svg=svg_plot(sharpes,'Sharpe theo mức phí','Phí trên mỗi chiều giao dịch','Sharpe năm',kind='bar',x_percent=True,benchmark=bs)
    (out/'sharpe_vs_fee.svg').write_text(svg,encoding='utf-8')
    sections.append('<div id="comparison"></div>'+card('So sánh độ nhạy với chi phí','Mỗi nhóm cột là một mức phí. Đường nét đứt là Sharpe của benchmark; cột có thể âm.',svg))
    heat_series={}
    displayed_rates=[]
    for name,runs in outputs.items():
        rate=.0025 if .0025 in runs else sorted(runs)[len(runs)//2]
        heat_series[name]=runs[rate].periods.net_return
        displayed_rates.append(f'{name}: {rate:.2%}')
    heat=monthly_heatmap(heat_series)
    (out/'monthly_returns_heatmap.svg').write_text(heat,encoding='utf-8')
    sections.append(card('Lợi nhuận phân bố qua từng tháng', 'Lợi suất sau phí. Mức phí minh họa: '+ '; '.join(displayed_rates)+'. Màu chỉ biểu thị dấu và độ lớn lợi suất, không phải mức xếp hạng rủi ro.',heat))
    sections.append('<div id="details"></div>')
    for name,results in outputs.items():
        curves=[]
        for rate,result in results.items():
            values=np.r_[1.,result.periods.end_value.to_numpy()]
            curves.append((f'Phí {rate*100:.2f}%',list(enumerate(values))))
        b=np.r_[1.,(1+benchmark.reindex(dates)).cumprod().to_numpy()]
        curves.append((cfg['benchmark_name'],list(enumerate(b))))
        equity=svg_plot(curves,f'{name} · Giá trị danh mục','Tháng ngoài mẫu','Giá trị / vốn ban đầu')
        # Show one disclosed fee in the area chart to avoid four almost-identical fills.
        selected=.0025 if .0025 in results else sorted(results)[len(results)//2]
        v=np.r_[1.,results[selected].periods.end_value.to_numpy()]
        dd=[(f'{name} · phí {selected*100:.2f}%',list(enumerate(v/np.maximum.accumulate(v)-1))),
            (cfg['benchmark_name'],list(enumerate(b/np.maximum.accumulate(b)-1)))]
        drawdown=svg_plot(dd,f'{name} · Sụt giảm từ đỉnh','Tháng ngoài mẫu','Drawdown (%)',kind='area',y_percent=True)
        (out/f'{name}_equity.svg').write_text(equity,encoding='utf-8')
        (out/f'{name}_drawdown.svg').write_text(drawdown,encoding='utf-8')
        sections.append(card(name,'Biểu đồ đường theo dõi giá trị qua thời gian; biểu đồ vùng nhấn mạnh các giai đoạn sụt giảm.',
            '<div class="chart-grid"><div>'+equity+'</div><div>'+drawdown+f'<p class="caption">Drawdown minh họa mức phí {selected*100:.2f}% và benchmark. Các mức phí còn lại nằm trong CSV chi tiết.</p></div></div>'))
    formatted=table.copy()
    names={'name':'Loại','strategy':'Chiến lược','transaction_cost_rate':'Phí / chiều','months':'Số tháng','sharpe':'Sharpe năm','cagr':'CAGR','max_drawdown':'Drawdown lớn nhất','total_return':'Lợi suất toàn kỳ','total_fee':'Tổng phí / vốn đầu','total_turnover_two_way':'Tổng turnover hai chiều'}
    for col in ['transaction_cost_rate','cagr','max_drawdown','total_return']:
        if col in formatted: formatted[col]=formatted[col].map(lambda x:f'{x:.2%}' if np.isfinite(x) else '—')
    for col in ['sharpe','total_fee','total_turnover_two_way']:
        if col in formatted: formatted[col]=formatted[col].map(lambda x:f'{x:.4f}' if np.isfinite(x) else '—')
    formatted=formatted.rename(columns=names)
    sections.append('<div id="data"></div>'+card('Bảng kết quả đầy đủ','Dấu — nghĩa là không áp dụng hoặc không xác định. Kéo ngang để xem đủ cột; CSV gốc giữ nguyên độ chính xác.', '<div class="table-wrap">'+formatted.to_html(index=False,border=0)+'</div>'))
    css="""*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f1f5f9;color:#172b4d;font:16px/1.65 Arial,sans-serif}main{max-width:1440px;margin:auto;padding:40px 28px}header{padding:12px 0 24px}h1{font-size:36px;line-height:1.2;margin:20px 0 12px}h2{font-size:23px;line-height:1.35;margin:0 0 10px}h3{font-size:15px;margin:0 0 10px}p{margin:0 0 16px}.version{margin-top:18px;color:#1d4ed8;font-weight:bold;font-size:13px;letter-spacing:1px}.badge{display:inline-block;background:#fff3d6;color:#815100;border:1px solid #f6d88a;border-radius:8px;padding:8px 14px;font-size:12px;font-weight:bold;letter-spacing:.6px}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin-bottom:24px}.stats div{background:#fff;padding:20px 24px;border:1px solid #dce5ef;border-radius:14px}.stats span{display:block;color:#63748b;font-size:14px}.stats strong{font-size:30px}nav{display:flex;gap:12px;flex-wrap:wrap;margin:0 0 28px}nav a{color:#1d4ed8;text-decoration:none;background:#e4edff;padding:8px 16px;border-radius:24px}.card{background:#fff;border:1px solid #dce5ef;border-radius:18px;padding:28px;margin-bottom:26px;box-shadow:0 4px 18px #10233f04}.muted,.caption{color:#63748b;font-size:14px}.caption{padding:0 24px}.notes{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;margin-top:20px}.notes div{border-left:3px solid #bfdbfe;padding-left:18px}.notes p{font-size:14px;margin:0}.chart-grid{display:grid;grid-template-columns:1fr;gap:24px}svg{display:block;width:100%;height:auto;max-width:1050px;margin:12px auto} .table-wrap{overflow-x:auto;margin-top:22px}table{border-collapse:collapse;width:100%;white-space:nowrap;font-size:13px}th{background:#eef3fa;color:#334863;text-align:right;padding:14px 16px}td{text-align:right;padding:13px 16px;border-bottom:1px solid #e7edf4}tr:nth-child(even){background:#f8fafc}td:first-child,th:first-child{text-align:left}@media(min-width:1500px){.chart-grid{grid-template-columns:1fr 1fr}}@media(max-width:650px){main{padding:20px 12px}.card{padding:18px}.notes{grid-template-columns:1fr}.stats{gap:8px}.stats div{padding:12px}h1{font-size:27px}}@media print{body{background:white}nav{display:none}.card{box-shadow:none;break-inside:avoid}main{padding:0}.table-wrap{overflow:visible}table{font-size:9px;white-space:normal}td,th{padding:5px}}"""
    page='<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>V5 · Báo cáo danh mục</title><style>'+css+'</style></head><body><main>'+''.join(sections)+'</main></body></html>'
    (out/'report.html').write_text(page,encoding='utf-8')
