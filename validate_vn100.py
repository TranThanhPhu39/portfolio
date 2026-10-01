"""Read-only audit of the group's period CSVs; no backup-folder inputs.
Usage: python validate_vn100.py --input main --output audit
No market returns are repaired or imputed by this script.
"""
import argparse, calendar, csv, datetime as dt, hashlib, json, math
from collections import defaultdict
from pathlib import Path

def number(value):
    try:
        x=float(value.replace(',', ''))
        return x if math.isfinite(x) else None
    except (ValueError, AttributeError): return None

def read(path):
    raw=path.read_bytes()
    try: text=raw.decode('utf-8-sig')
    except UnicodeDecodeError: text=raw.decode('cp1252')
    return list(csv.DictReader(text.splitlines()))

def save(path, rows, columns):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(rows)

def audit(source, output):
    files=sorted(source.glob('Top100_Ky*.csv'))
    if not files: raise ValueError('No Top100_Ky*.csv files found')
    output.mkdir(parents=True,exist_ok=True)
    rows=[];manifest=[]
    for file in files:
        manifest.append({'file':file.name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
        for r in read(file):
            r['_date']=dt.datetime.strptime(r['Date'],'%d/%m/%Y').date()
            r['_file']=file.name;rows.append(r)
    grouped=defaultdict(list);months=defaultdict(set);keys=set();duplicates=[]
    for r in rows:
        key=(r['Ticker'],r['_date'])
        if key in keys:duplicates.append({'ticker':key[0],'date':str(key[1])})
        keys.add(key);grouped[r['Ticker']].append(r);months[r['_date']].add(r['Ticker'])
    mismatches=[];missing=[];incomplete=[];comparisons=0
    for ticker,rr in grouped.items():
        rr.sort(key=lambda r:r['_date'])
        for r in rr:
            if number(r['Close (EOM)']) is None:
                missing.append({'ticker':ticker,'date':str(r['_date']),'given_return_percent':r['Monthly Return (%)'],'source_file':r['_file']})
            if r['_date'].day!=calendar.monthrange(r['_date'].year,r['_date'].month)[1]:
                incomplete.append({'ticker':ticker,'date':str(r['_date']),'source_file':r['_file']})
        for a,b in zip(rr,rr[1:]):
            da,db=a['_date'],b['_date']
            if (db.year-da.year)*12+db.month-da.month!=1:continue
            p,q=number(a['Close (EOM)']),number(b['Close (EOM)'])
            given=number(b['Monthly Return (%)'])
            if p is None or q is None or p<=0 or q<=0 or given is None:continue
            comparisons+=1;calculated=(q/p-1)*100;diff=given-calculated
            # 0.02 percentage point screening tolerance; not a source correction.
            if abs(diff)>.02:
                mismatches.append({'ticker':ticker,'date':str(db),'previous_price':p,'price':q,'given_return_percent':given,'price_return_percent':calculated,'difference_percentage_points':diff,'source_file':b['_file']})
    mismatches.sort(key=lambda r:abs(r['difference_percentage_points']),reverse=True)
    # Same month series should be unique across constituent rows.
    factors=defaultdict(lambda:defaultdict(set))
    for r in rows:
        for c in ('rRF','VN30'): factors[r['_date']][c].add(r[c])
    conflicts=[{'date':str(d),'column':c,'values':'|'.join(sorted(v))} for d,cols in factors.items() for c,v in cols.items() if len(v)!=1]
    # Diagnostic eligibility based solely on past presence in period files.
    # Missing pre-membership history does not imply the security did not trade.
    dates=sorted(months);coverage=[]
    for pos in range(25,len(dates)):
        training=dates[pos-25:pos-1]
        members=months[dates[pos]]
        full=sum(all((t,d) in keys for d in training) for t in members)
        coverage.append({'date':str(dates[pos]),'members':len(members),'members_with_24_training_rows':full,'without_full_training_history':len(members)-full})
    summary={'status':'NOT_READY_FOR_RESEARCH_BACKTEST','input_scope':'Only VN100 period folder; no backup input used','files':len(files),'rows':len(rows),'unique_tickers':len(grouped),'months':len(dates),'first_date':str(dates[0]),'last_date':str(dates[-1]),'duplicate_keys':len(duplicates),'adjacent_price_pairs_checked':comparisons,'return_price_mismatches_over_0_02_percentage_points':len(mismatches),'missing_prices':len(missing),'non_calendar_month_end_rows':len(incomplete),'RF_min':min(number(r['rRF']) for r in rows),'RF_max':max(number(r['rRF']) for r in rows),'RF_unit':'Not established from period files; annual-versus-monthly must be confirmed','series_conflicts':len(conflicts),'training_window':24,'lag_months':1,'evaluation_months_missing_some_member_history':sum(x['without_full_training_history']>0 for x in coverage),'official_VN100_membership':'Not established; constituent file contains rankings and Market_Cap','backtest_performed':False}
    save(output/'return_price_mismatches.csv',mismatches,['ticker','date','previous_price','price','given_return_percent','price_return_percent','difference_percentage_points','source_file'])
    save(output/'missing_prices.csv',missing,['ticker','date','given_return_percent','source_file'])
    save(output/'non_month_end_rows.csv',incomplete,['ticker','date','source_file'])
    save(output/'training_coverage.csv',coverage,['date','members','members_with_24_training_rows','without_full_training_history'])
    save(output/'series_conflicts.csv',conflicts,['date','column','values'])
    (output/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    (output/'source_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2,ensure_ascii=True));return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,default=Path(__file__).parent/'main');p.add_argument('--output',type=Path,default=Path(__file__).parent/'audit');args=p.parse_args();audit(args.input,args.output)
