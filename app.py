import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title='NSE Quantitative Trading Dashboard', page_icon='📈', layout='wide', initial_sidebar_state='expanded')
BASE = Path(__file__).resolve().parent
OUTPUT = BASE / 'output'
REPORTS = {
    'All Scores':'all_scores.csv',
    'Next-Day Candidates':'next_day_candidates.csv',
    'Swing Candidates':'swing_candidates.csv',
    'Historical Setup Stats':'historical_setup_stats.csv',
    'Position Selection':'position_selection.csv',
    'High-Priority Overlap':'high_priority_overlap.csv',
}

st.markdown('''<style>
.block-container{max-width:1900px;padding:1.2rem 2rem 3rem}
.card{border:1px solid rgba(128,128,128,.25);border-radius:14px;padding:16px}
</style>''', unsafe_allow_html=True)

@st.cache_data(ttl=300, show_spinner=False)
def load_csv(name):
    p = OUTPUT / name
    if not p.exists(): return pd.DataFrame()
    try:
        d = pd.read_csv(p, low_memory=False)
        d.columns = [str(c).strip().replace('\n',' ') for c in d.columns]
        return d
    except Exception as e:
        return pd.DataFrame({'_READ_ERROR_':[str(e)]})

def symbol_col(df):
    if df.empty: return None
    for c in ['SYMBOL','Symbol','symbol','STOCK','Stock','TICKER','Ticker','SECURITY','Security']:
        if c in df.columns: return c
    for c in df.columns:
        u=str(c).upper()
        if 'SYMBOL' in u or 'TICKER' in u: return c
    return None

def fmt(v):
    if pd.isna(v): return '—'
    if isinstance(v,float): return f'{v:,.4f}'.rstrip('0').rstrip('.')
    return str(v)

reports = {k:load_csv(v) for k,v in REPORTS.items()}

st.title('📈 NSE Quantitative Trading Dashboard')
st.caption('Exact scanner reports • no mandatory filters • six-report research view')
mods=[]
for f in REPORTS.values():
    p=OUTPUT/f
    if p.exists(): mods.append(datetime.fromtimestamp(p.stat().st_mtime))
if mods: st.info(f'Latest report update: {max(mods):%d-%b-%Y %H:%M:%S}')

all_df=reports['All Scores']; next_df=reports['Next-Day Candidates']; swing_df=reports['Swing Candidates']; pos_df=reports['Position Selection']; overlap_df=reports['High-Priority Overlap']
c=st.columns(6)
for box,title,df in zip(c,['All Scores','Next-Day','Swing','Position','High Priority','Reports Loaded'],[all_df,next_df,swing_df,pos_df,overlap_df,None]):
    box.metric(title, f'{len(reports) if df is None else len(df):,}' if df is not None else f'{sum(not x.empty for x in reports.values())}/6')

if 'analysis_symbol' not in st.session_state: st.session_state.analysis_symbol=None

st.markdown('## 📊 Generated Reports')
tabs=st.tabs(list(REPORTS))
for tab,(name,filename) in zip(tabs,REPORTS.items()):
    with tab:
        df=reports[name]
        if df.empty:
            st.warning(f'{name}: file missing or empty. Expected output/{filename}')
            continue
        st.write(f'**Rows:** {len(df):,}  |  **Columns:** {len(df.columns):,}')
        q=st.text_input('Search (optional)', key='q_'+name, placeholder='Leave blank to show the complete report')
        view=df
        if q.strip():
            mask=view.astype(str).apply(lambda s:s.str.contains(q.strip(),case=False,na=False)).any(axis=1)
            view=view.loc[mask]
        try:
            ev=st.dataframe(view, hide_index=True, width='stretch', height=650, on_select='rerun', selection_mode='single-row')
            rows=getattr(ev.selection,'rows',[]) if ev else []
        except TypeError:
            st.dataframe(view, hide_index=True, width='stretch', height=650)
            rows=[]
        if rows:
            sc=symbol_col(view)
            if sc:
                sym=str(view.iloc[rows[0]][sc])
                st.session_state.analysis_symbol=sym
                st.success(f'Selected {sym}. Use the Stock Analysis section below.')

sym=st.session_state.analysis_symbol
if sym:
    st.markdown('---')
    st.header(f'🔬 Stock Analysis — {sym}')
    if st.button('Close Stock Analysis'): st.session_state.analysis_symbol=None; st.rerun()
    found=[]
    for name,df in reports.items():
        sc=symbol_col(df)
        if sc:
            m=df[df[sc].astype(str).str.upper().eq(sym.upper())]
            if not m.empty: found.append((name,m))
    if not found: st.warning('No matching rows found in the six reports.')
    else:
        for name,m in found:
            st.subheader(name); st.dataframe(m,hide_index=True,width='stretch',height=min(500,120+35*len(m)))
        common={}
        keys=['BIAS','CONFIDENCE','SCORE','NEXT_DAY_SCORE','SWING_SCORE','HISTORICAL_SCORE','POSITION_SCORE','FACTOR_RATIO','ALIGNED_FACTORS','CMP','EXPECTED_RANGE_LOW_PCT','EXPECTED_RANGE_HIGH_PCT','INVALIDATION','PRIMARY_DRIVER','CONFLICTING_SIGNAL','TRADE_MODE','IN_NEXT_DAY','IN_SWING','OVERLAP']
        for _,m in found:
            r=m.iloc[0]
            for k in keys:
                if k in r.index and k not in common: common[k]=r[k]
        if common:
            st.subheader('Key fields'); cc=st.columns(4)
            for i,(k,v) in enumerate(common.items()): cc[i%4].metric(k.replace('_',' '),fmt(v))

st.markdown('---')
st.caption('Research/ranking tool only. Scores are not guaranteed returns; leverage magnifies gains and losses.')
