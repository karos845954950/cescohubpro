
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import feedparser
import requests
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from streamlit_autorefresh import st_autorefresh
import os, json, math

st.set_page_config(page_title="NASDAQ MACRO DESK", page_icon="▰", layout="wide", initial_sidebar_state="expanded")

# ---------- Institutional visual system ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] {font-family:'Manrope',sans-serif;}
.stApp {background:#0a0f16;color:#e7edf5;}
[data-testid="stSidebar"] {background:#0e1621;border-right:1px solid #263244;}
.block-container {padding-top:1.2rem;padding-bottom:2rem;max-width:1600px;}
h1,h2,h3 {letter-spacing:-.04em;}
.metric-card {background:linear-gradient(145deg,#131f2d,#101923);border:1px solid #29384a;border-radius:12px;padding:16px 18px;min-height:108px;}
.eyebrow {color:#8ea2b9;font-size:10px;letter-spacing:.16em;font-weight:800;text-transform:uppercase;}
.big-value {font-size:27px;font-weight:800;letter-spacing:-.04em;color:#f2f6fb;margin-top:5px;}
.sub-value {font-size:11px;color:#91a3b8;margin-top:4px;}
.signal-bull {color:#35d39a;font-weight:800;}
.signal-bear {color:#ff6d78;font-weight:800;}
.signal-neutral {color:#e5bd68;font-weight:800;}
.panel {background:#101923;border:1px solid #263547;border-radius:12px;padding:18px;}
.small-muted {color:#91a3b8;font-size:12px;}
hr {border-color:#263547 !important;}
div[data-testid="stDataFrame"] {border:1px solid #263547;border-radius:8px;}
.stButton>button {border-radius:8px;border:1px solid #34465b;background:#182536;color:#e7edf5;font-weight:700;}
.stButton>button:hover {border-color:#5c789a;color:white;}
</style>
""", unsafe_allow_html=True)

ROME = ZoneInfo("Europe/Rome")
now = datetime.now(ROME)
today_key = now.strftime("%Y-%m-%d")

def card(label, value, sub=""):
    st.markdown(f"""<div class="metric-card"><div class="eyebrow">{label}</div>
    <div class="big-value">{value}</div><div class="sub-value">{sub}</div></div>""", unsafe_allow_html=True)

def safe_float(x):
    try:
        return float(x)
    except Exception:
        return np.nan

@st.cache_data(ttl=300, show_spinner=False)
def get_yahoo(symbol, period="5d", interval="15m"):
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=False, threads=False)
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna(how="all")
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=900, show_spinner=False)
def get_rss(url, limit=12):
    try:
        feed = feedparser.parse(url)
        out=[]
        for e in feed.entries[:limit]:
            out.append({"Ora/data": getattr(e,"published",""), "Titolo": getattr(e,"title",""), "Link": getattr(e,"link","")})
        return pd.DataFrame(out)
    except Exception:
        return pd.DataFrame(columns=["Ora/data","Titolo","Link"])

@st.cache_data(ttl=3600, show_spinner=False)
def fred_series(series_id, api_key):
    if not api_key:
        return pd.DataFrame()
    try:
        url="https://api.stlouisfed.org/fred/series/observations"
        r=requests.get(url, params={"series_id":series_id,"api_key":api_key,"file_type":"json","sort_order":"desc","limit":30}, timeout=12)
        r.raise_for_status()
        rows=r.json().get("observations",[])
        df=pd.DataFrame(rows)
        if df.empty: return df
        df["value"]=pd.to_numeric(df["value"],errors="coerce")
        return df.dropna(subset=["value"])
    except Exception:
        return pd.DataFrame()

def last_close(df):
    if df.empty or "Close" not in df: return np.nan
    s=df["Close"].dropna()
    return safe_float(s.iloc[-1]) if len(s) else np.nan

def pct_change_n(df, n=4):
    if df.empty or "Close" not in df: return np.nan
    s=df["Close"].dropna()
    if len(s)<=n: return np.nan
    return float((s.iloc[-1]/s.iloc[-1-n]-1)*100)

def score_direction(x, positive=0.0, negative=0.0):
    if not np.isfinite(x): return 0
    if x > positive: return 1
    if x < negative: return -1
    return 0

# ---------- Sidebar ----------
st.sidebar.markdown("## ▰ NASDAQ MACRO DESK")
st.sidebar.caption("INSTITUTIONAL RESEARCH TERMINAL")
st.sidebar.markdown("---")
st.sidebar.markdown("**CONFIGURAZIONE DATI**")
fred_key = st.sidebar.text_input("FRED API key (facoltativa)", type="password", value=os.getenv("FRED_API_KEY",""))
refresh = st.sidebar.selectbox("Aggiornamento automatico", ["5 minuti","15 minuti","30 minuti","Manuale"], index=0)
refresh_ms = {"5 minuti":300000,"15 minuti":900000,"30 minuti":1800000}.get(refresh)
if refresh_ms:
    st_autorefresh(interval=refresh_ms, key="market_refresh")
st.sidebar.caption("I dati si aggiornano mentre la pagina è aperta. La cache può introdurre ritardi.")
st.sidebar.markdown("---")
st.sidebar.markdown("**DATI OPZIONI**")
st.sidebar.caption("Carica un CSV del tuo provider (QQQ / NDX / NQ options). Il flusso non viene inventato se manca una fonte.")
flow_file = st.sidebar.file_uploader("Importa options flow CSV", type=["csv"])
st.sidebar.markdown("---")
if st.sidebar.button("↻ Aggiorna ora", use_container_width=True):
    st.cache_data.clear()
    st.rerun()
st.sidebar.caption(f"Orario locale: {now.strftime('%d/%m/%Y %H:%M:%S')} CET/CEST")

# ---------- Header ----------
st.markdown("<div class='eyebrow'>US EQUITY INDEX FUTURES · DAILY RESEARCH</div>", unsafe_allow_html=True)
st.title("NASDAQ MACRO DESK")
st.markdown(f"<div class='small-muted'>NQ1! · Session brief · {now.strftime('%A %d %B %Y')} · Europe/Rome</div>", unsafe_allow_html=True)
st.markdown("---")

# ---------- Market data ----------
symbols = {
    "NQ=F":"Nasdaq futures proxy",
    "ES=F":"S&P 500 futures",
    "^VIX":"VIX",
    "^TNX":"US 10Y yield",
    "DX-Y.NYB":"US Dollar Index",
    "GC=F":"Gold",
    "CL=F":"WTI crude"
}
with st.spinner("Raccolta dati di mercato..."):
    market = {s:get_yahoo(s) for s in symbols}

nq = market["NQ=F"]
es = market["ES=F"]
vix = market["^VIX"]
tnx = market["^TNX"]
dxy = market["DX-Y.NYB"]
gold = market["GC=F"]
oil = market["CL=F"]

nq_last=last_close(nq); nq_mom=pct_change_n(nq,4); es_mom=pct_change_n(es,4)
vix_last=last_close(vix); vix_mom=pct_change_n(vix,4)
tnx_last=last_close(tnx); tnx_mom=pct_change_n(tnx,4)
dxy_last=last_close(dxy); dxy_mom=pct_change_n(dxy,4)

# ---------- Daily model: transparent weighted ensemble ----------
components=[]
def add_component(name, raw, weight, explanation, available=True):
    if available and np.isfinite(raw):
        components.append({"Fattore":name,"Segnale":int(raw),"Peso":weight,"Contributo":int(raw)*weight,"Lettura":explanation})

add_component("NQ momentum", score_direction(nq_mom,0.03,-0.03), 3, "Momentum breve del future proxy", np.isfinite(nq_mom))
add_component("ES confirmation", score_direction(es_mom,0.02,-0.02), 2, "Conferma / divergenza S&P 500", np.isfinite(es_mom))
add_component("VIX regime", score_direction(-vix_mom,0.5,-0.5), 2, "VIX in calo favorisce risk-on", np.isfinite(vix_mom))
add_component("10Y yield", score_direction(-tnx_mom,0.05,-0.05), 2, "Rendimenti in calo favoriscono duration", np.isfinite(tnx_mom))
add_component("Dollar index", score_direction(-dxy_mom,0.03,-0.03), 1, "Dollaro in calo è marginalmente favorevole", np.isfinite(dxy_mom))

denom=sum(x["Peso"] for x in components)
raw_score=(sum(x["Contributo"] for x in components)/denom*100) if denom else 0
coverage=len(components)/5
agreement=(abs(sum(x["Contributo"] for x in components))/denom) if denom else 0
if denom < 5:
    bias="INSUFFICIENT DATA"
    bias_class="signal-neutral"
elif raw_score >= 25:
    bias="BULLISH"
    bias_class="signal-bull"
elif raw_score <= -25:
    bias="BEARISH"
    bias_class="signal-bear"
else:
    bias="NEUTRAL"
    bias_class="signal-neutral"

# Agreement score is NOT hit-rate or probability.
confidence_label = "LOW" if coverage < .8 or agreement < .25 else ("MODERATE" if agreement < .6 else "ELEVATED")
confidence_note = "Concordanza dei fattori disponibili; non è una probabilità di successo."

# ---------- Main signal ----------
c1,c2,c3,c4 = st.columns([1.25,1,1,1])
with c1:
    st.markdown(f"""<div class="metric-card"><div class="eyebrow">DAILY DIRECTIONAL BIAS</div>
    <div class="big-value {bias_class}">{bias}</div><div class="sub-value">Model score: {raw_score:+.0f} / 100 · {len(components)}/5 fattori disponibili</div></div>""",unsafe_allow_html=True)
with c2: card("NQ FUTURES PROXY", f"{nq_last:,.2f}" if np.isfinite(nq_last) else "N/D", f"Momentum breve {nq_mom:+.2f}%" if np.isfinite(nq_mom) else "Dato non disponibile")
with c3: card("VIX", f"{vix_last:.2f}" if np.isfinite(vix_last) else "N/D", f"Var. breve {vix_mom:+.2f}%" if np.isfinite(vix_mom) else "Dato non disponibile")
with c4: card("FACTOR AGREEMENT", confidence_label, confidence_note)

st.markdown("")
if bias == "INSUFFICIENT DATA":
    st.warning("Copertura dati insufficiente: il modello non pubblica un bias direzionale.")
elif confidence_label == "LOW":
    st.warning("Segnale fragile: fattori poco concordi o dati mancanti. Preferire NEUTRAL / NO TRADE.")
else:
    st.info("Bias quantitativo preliminare. Va validato con price action, livelli e calendario prima di qualsiasi decisione.")

# ---------- Chart ----------
st.markdown("### NQ · Intraday context")
if not nq.empty and "Close" in nq:
    chart_df=nq.tail(100).copy()
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=chart_df.index,y=chart_df["Close"],mode="lines",name="NQ proxy",line=dict(color="#55a7ff",width=2)))
    fig.update_layout(template="plotly_dark",height=330,margin=dict(l=10,r=10,t=10,b=10),paper_bgcolor="#101923",plot_bgcolor="#101923",xaxis_title="",yaxis_title="Price",legend=dict(orientation="h"))
    st.plotly_chart(fig,use_container_width=True)
else:
    st.warning("Prezzi NQ non disponibili dal provider Yahoo in questo momento. Controlla più tardi o configura una fonte dati professionale.")

# ---------- Factors ----------
left,right=st.columns([1.1,1])
with left:
    st.markdown("### Cross-asset dashboard")
    cross=[]
    for sym,label,df,mom in [
        ("NQ=F","Nasdaq futures proxy",nq,nq_mom),("ES=F","S&P 500 futures",es,es_mom),
        ("^VIX","VIX",vix,vix_mom),("^TNX","US 10Y yield",tnx,tnx_mom),
        ("DX-Y.NYB","US Dollar Index",dxy,dxy_mom),("GC=F","Gold",gold,pct_change_n(gold,4)),
        ("CL=F","WTI crude",oil,pct_change_n(oil,4))]:
        cross.append({"Mercato":label,"Ultimo":round(last_close(df),3) if np.isfinite(last_close(df)) else None,"Var. breve %":round(mom,3) if np.isfinite(mom) else None,"Stato":"OK" if not df.empty else "MISSING"})
    st.dataframe(pd.DataFrame(cross),hide_index=True,use_container_width=True)
with right:
    st.markdown("### Model decomposition")
    if components:
        comp=pd.DataFrame(components)
        comp["Direzione"]=comp["Segnale"].map({1:"Bullish",-1:"Bearish",0:"Neutral"})
        st.dataframe(comp[["Fattore","Direzione","Peso","Contributo","Lettura"]],hide_index=True,use_container_width=True)
    else:
        st.info("Nessun fattore disponibile.")

# ---------- Macro / news ----------
st.markdown("---")
st.markdown("### Macro intelligence")
news_sources = [
    ("Federal Reserve","https://www.federalreserve.gov/feeds/press_all.xml"),
    ("BLS","https://www.bls.gov/feed/news_release/empsit.rss"),
    ("BEA","https://www.bea.gov/news/rss.xml"),
]
news_cols=st.columns(3)
for col,(name,url) in zip(news_cols,news_sources):
    with col:
        st.markdown(f"**{name}**")
        feed=get_rss(url,8)
        if feed.empty:
            st.caption("Feed momentaneamente non disponibile.")
        else:
            for _,r in feed.head(5).iterrows():
                title=str(r["Titolo"])
                link=str(r["Link"])
                st.markdown(f"• [{title}]({link})")
                if r["Ora/data"]: st.caption(str(r["Ora/data"]))

# FRED optional panel
if fred_key:
    st.markdown("#### Macro series · FRED")
    fcols=st.columns(3)
    for col,(sid,label) in zip(fcols,[("DFF","Fed Funds Rate"),("DGS10","10Y Treasury"),("UNRATE","Unemployment")]):
        with col:
            f=fred_series(sid,fred_key)
            if not f.empty:
                st.metric(label, f"{f.iloc[0]['value']:.2f}", f.iloc[0]["date"])
            else:
                st.metric(label,"N/D","API non disponibile")

# ---------- Options flow ----------
st.markdown("---")
st.markdown("### Options flow & dealer positioning")
st.caption("Il modulo accetta dati importati da un provider. Senza un feed autorizzato non mostra valori sintetici o inventati.")
if flow_file is not None:
    try:
        flow=pd.read_csv(flow_file)
        st.success(f"File caricato: {len(flow)} righe.")
        st.caption("Colonne riconosciute automaticamente quando presenti: symbol, expiration, strike, option_type, volume, open_interest, premium, side, timestamp.")
        st.dataframe(flow.head(30),use_container_width=True)
        cols={c.lower():c for c in flow.columns}
        if "option_type" in cols and "volume" in cols:
            typ=flow[cols["option_type"]].astype(str).str.lower()
            vol=pd.to_numeric(flow[cols["volume"]],errors="coerce").fillna(0)
            calls=vol[typ.str.contains("call|c")].sum()
            puts=vol[typ.str.contains("put|p")].sum()
            if calls+puts>0:
                ratio=calls/puts if puts else np.inf
                a,b=st.columns(2)
                a.metric("Call volume",f"{calls:,.0f}")
                b.metric("Put volume",f"{puts:,.0f}")
                st.metric("Call / Put volume ratio", "∞" if np.isinf(ratio) else f"{ratio:.2f}")
        else:
            st.info("Per calcolare il riepilogo servono almeno le colonne option_type e volume.")
    except Exception as e:
        st.error(f"CSV non leggibile: {e}")
else:
    st.info("Nessun options flow collegato. Possiamo collegare in seguito un provider con API e licenza dati (ad esempio feed opzioni CME o provider specializzati su NDX/QQQ).")
    st.markdown("[CME Group · API dati futures e opzioni](https://www.cmegroup.com/market-data/market-data-api.html)")

# ---------- Scenarios & guardrails ----------
st.markdown("---")
st.markdown("### Session playbook")
p1,p2,p3=st.columns(3)
with p1:
    st.markdown('<div class="panel"><div class="eyebrow">PRIMARY SCENARIO</div><h3>Follow-through</h3><p class="small-muted">Valutare continuazione solo se NQ conferma il bias con struttura intraday e partecipazione ES.</p></div>',unsafe_allow_html=True)
with p2:
    st.markdown('<div class="panel"><div class="eyebrow">ALTERNATIVE SCENARIO</div><h3>Failed move</h3><p class="small-muted">Se prezzo e cross-asset divergono, ridurre la convinzione e attendere conferma o rientro nel range.</p></div>',unsafe_allow_html=True)
with p3:
    st.markdown('<div class="panel"><div class="eyebrow">INVALIDATION</div><h3>Regime shift</h3><p class="small-muted">Un dato macro, una variazione dei rendimenti o un reversal del VIX può invalidare il bias iniziale.</p></div>',unsafe_allow_html=True)

# ---------- Reliability / methodology ----------
with st.expander("Metodologia, limiti e attendibilità"):
    st.markdown("""
    **Questo è un motore quantitativo preliminare, non un modello con accuratezza dimostrata.**
    - Il punteggio combina momentum NQ, conferma ES, VIX, Treasury 10Y e DXY con pesi espliciti.
    - Il valore “factor agreement” misura la concordanza dei fattori disponibili, NON la probabilità che il mercato salga/scenda e NON la percentuale di previsioni corrette.
    - I prezzi Yahoo (`NQ=F`) sono un proxy e non equivalgono al contratto continuo TradingView `NQ1!`; disponibilità, ritardi e licenze dipendono dal provider.
    - Il feed opzioni è volutamente vuoto finché non viene collegata una fonte autorizzata. Un semplice call/put volume non basta a inferire il lato aggressore o il posizionamento dealer.
    - Prima di mostrare una percentuale di accuratezza, il modello deve superare backtest walk-forward, costi/slippage, test out-of-sample e monitoraggio live con previsioni archiviate prima dell'esito.
    - Non è consulenza finanziaria né un sistema di esecuzione ordini.
    """)
st.caption(f"Build 2.0 · Session date {today_key} · Refresh/cache: market 5m, news 15m, FRED 60m · Data availability may vary.")
