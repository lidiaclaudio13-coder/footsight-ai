import streamlit as st
import pandas as pd
from src.core.db import init_db
from src.decision.single_finder import find_top_singles
from src.decision.accumulator import build_accumulator
from src.decision.tracker import get_performance_summary
from src.models.ai_agent import analyze_with_ollama
from src.datasources.football_data import ingest_football_data
from src.datasources.news_injuries import parse_all_rss_feeds
from src.features.rolling_stats import build_all_features

st.set_page_config(page_title="FootSight AI + Groq", page_icon="⚽", layout="wide")

st.title("⚽ FootSight AI — Control Panel & Agente Cloud")

# Assicura l'inizializzazione del DB all'avvio senza far crashare il server
try:
    init_db()
except Exception as e:
    st.warning(f"Inizializzazione DB: {e}")

# Sidebar
st.sidebar.header("⚙️ Azioni Pipeline")
if st.sidebar.button("🚀 Esegui Pipeline Dati"):
    with st.spinner("Aggiornamento dati in corso..."):
        try:
            ingest_football_data()
            parse_all_rss_feeds()
            build_all_features()
            st.success("Pipeline completata!")
        except Exception as e:
            st.error(f"Errore durante l'esecuzione della pipeline: {e}")

if st.sidebar.button("🧹 Inizializza DB"):
    try:
        init_db()
        st.success("Database Pronto e Ripristinato!")
    except Exception as e:
        st.error(f"Errore ripristino DB: {e}")

# Tabs
tab1, tab2, tab3 = st.tabs(["📌 Value Bets Singole", "🎯 Schedina Multipla", "📊 Performance Tracker"])

with tab1:
    st.header("Ricerca Singole Value Bets")
    col1, col2 = st.columns(2)
    with col1:
        top_n = st.slider("Numero di Singole da mostrare", 1, 10, 5)
    with col2:
        max_s_odd = st.slider("Quota Massima Singola", 1.50, 5.00, 3.50)

    if st.button("🔍 Calcola Singole con Groq AI"):
        with st.spinner("Elaborazione singole e analisi Groq..."):
            singles = find_top_singles(top_n=top_n, max_single_odds=max_s_odd)
            if singles:
                for s in singles:
                    with st.expander(f"⚽ {s['match']} — {s['selection']} (Quota: {s['odds']:.2f})"):
                        c_a, c_b = st.columns([1, 2])
                        with c_a:
                            st.write(f"**Lega**: {s['league']}")
                            st.write(f"**Probabilità**: {s['prob_est']*100:.1f}%")
                            st.write(f"**EV**: +{s['ev']:.4f}")
                            st.write(f"**Stake Kelly**: {s['stake_pct']}%")
                        with c_b:
                            st.markdown("### 🤖 Valutazione Groq AI")
                            ai_op = analyze_with_ollama(s['match'], s['selection'], s['odds'], s['prob_est'], s['ev'])
                            st.info(ai_op)
            else:
                st.warning("Nessuna singola trovata. Esegui la pipeline se il database è vuoto.")

with tab2:
    st.header("🎯 Generatore Schedina Multipla Personalizzata")
    
    st.markdown("### 1. Impostazioni Quota Totale e Singola")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        min_acc_odd = st.number_input("Quota Totale MIN", min_value=1.5, max_value=100.0, value=3.0, step=0.5)
    with c2:
        max_acc_odd = st.number_input("Quota Totale MAX", min_value=2.0, max_value=500.0, value=25.0, step=1.0)
    with c3:
        single_min_odd = st.number_input("Quota Singola MIN (x evento)", min_value=1.10, max_value=10.0, value=1.25, step=0.05)
    with c4:
        single_max_odd = st.number_input("Quota Singola MAX (x evento)", min_value=1.20, max_value=20.0, value=4.00, step=0.10)

    st.markdown("### 2. Modalità Numero Eventi")
    mode_eventi = st.radio("Scegli criterio eventi:", ["Range (Min - Max)", "Numero Esatto"], horizontal=True)

    exact_ev = None
    min_ev_cnt = 2
    max_ev_cnt = 6

    if mode_eventi == "Numero Esatto":
        exact_ev = st.number_input("Numero Esatto di Eventi in schedina", min_value=2, max_value=12, value=4, step=1)
    else:
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            min_ev_cnt = st.slider("Numero MIN Eventi", 2, 10, 3)
        with col_e2:
            max_ev_cnt = st.slider("Numero MAX Eventi", 2, 12, 6)

    if st.button("🚀 Calcola Multipla Personalizzata"):
        with st.spinner("Ricerca della combinazione ottimale..."):
            acc = build_accumulator(
                target_min_odds=float(min_acc_odd),
                target_max_odds=float(max_acc_odd),
                min_events=int(min_ev_cnt),
                max_events=int(max_ev_cnt),
                exact_events=exact_ev,
                single_min_odd=float(single_min_odd),
                single_max_odd=float(single_max_odd)
            )
            if acc:
                st.success(f"🎯 Multipla Trovata ({acc['num_events']} eventi)! Quota Totale: {acc['total_odds']} | Probabilità Combinata: {acc['combined_prob']}%")
                df_acc = pd.DataFrame(acc["events"])
                st.dataframe(df_acc[["league", "match", "selection", "odds", "prob", "ev"]], width="stretch")
            else:
                st.error("Nessuna combinazione soddisfa i criteri scelti. Prova ad allargare il range della quota totale o ad abbassare la Quota Singola MIN.")

with tab3:
    st.header("Performance Reali Bankroll")
    summary = get_performance_summary()
    st.json(summary)
