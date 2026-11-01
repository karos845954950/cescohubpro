# NASDAQ MACRO DESK — Pro starter

Dashboard Streamlit in italiano per un briefing giornaliero sui futures Nasdaq.

## Cosa fa
- Bias preliminare BULLISH / BEARISH / NEUTRAL con score trasparente.
- Cross-asset: NQ proxy, ES, VIX, Treasury 10Y, DXY, oro e petrolio.
- Feed RSS ufficiali Fed, BLS e BEA.
- Serie FRED opzionali (serve una API key gratuita).
- Import CSV per options flow: mostra i dati effettivamente caricati e calcola statistiche base se le colonne sono presenti.
- Refresh automatico mentre la pagina è aperta.

## Limiti importanti
Questa è una base tecnica seria, ma NON dichiara un'accuratezza del 90%. Il punteggio di concordanza non è una probabilità di successo. Non si devono trasformare euristiche in promesse di rendimento.
Yahoo `NQ=F` è un proxy e non equivale al contratto continuo TradingView `NQ1!`. Per dati futures e opzioni real-time affidabili servono provider autorizzati e licenze exchange.
Il modulo options flow importa CSV; non inventa flow quando non è collegato un provider. CME offre API per futures/opzioni, ma accesso e licenze vanno verificati con CME: https://www.cmegroup.com/market-data/market-data-api.html

## Avvio locale Windows
1. Installa Python 3.11 o 3.12.
2. Estrai lo ZIP.
3. Apri il prompt nella cartella e lancia:
   `py -m venv .venv`
   `.venv\\Scripts\\activate`
   `pip install -r requirements.txt`
   `streamlit run app.py`

## Pubblicazione Streamlit Community Cloud
- Carica `app.py` e `requirements.txt` nella root di un repository GitHub.
- In Streamlit Community Cloud scegli il repository e `app.py` come Main file path.
- Se vuoi FRED: Settings → Secrets e aggiungi:
  `FRED_API_KEY = "la_tua_chiave"`
  Ottieni la chiave da https://fred.stlouisfed.org/docs/api/api_key.html

## Options flow CSV
Carica un CSV dal tuo provider. Colonne riconosciute:
`symbol, expiration, strike, option_type, volume, open_interest, premium, side, timestamp`
Per il calcolo base sono richieste `option_type` e `volume`.
Per distinguere acquisti a bid/ask, sweep, opening/closing e dealer gamma serve un feed più ricco e documentato.

## Roadmap per renderlo un research system verificabile
1. Provider dati NQ/ES e opzioni con licenza e timestamp.
2. Calendario macro strutturato con consenso, actual, previous e surprise.
3. News classification + event impact con citazioni e timestamp.
4. GEX/DEX, skew, IV term structure, put/call, unusual trades e aggressor-side.
5. Archivio immutabile del bias pre-market e di ogni aggiornamento intraday.
6. Backtest walk-forward e report hit-rate per orizzonte (open→close, 30m, 2h), regime e giorno evento.
7. Solo dopo validazione: calibrazione probabilistica; mai dichiarare 90% senza prova out-of-sample.

## GitHub Actions
Lo starter include un workflow manuale/programmabile come punto di partenza, ma Streamlit Cloud non garantisce esecuzione pianificata se l'app dorme. Il workflow non è configurato per scaricare o pubblicare segnali automaticamente.
