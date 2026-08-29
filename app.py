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

st.set_page_config(page_title="FootSight AI + Ollama", page_icon="⚽", layout="wide")

st.title("⚽ FootSight AI — Control Panel & Agente Ollama")

# Sidebar
st.sidebar.header("⚙️ Azioni Pipeline")
if st.sidebar.button("🚀 Esegui Pipeline Dati"):
    with st.spinner("Aggiornamento dati in corso..."):
        ingest_football_data()
        parse_all_rss_feeds()
        build_all_features()
        st.success("Pipeline completata!")

if st.sidebar.button("🧹 Inizializza DB"):
    init_db()
    st.success("Database Pronto!")

tab1, tab2, tab3 = st.tabs(["📌 Value Bets Singole", "🎯 Schedina Multipla", "📊 Performance Tracker"])

with tab1:
    st.header("Ricerca Singole Value Bets")
    col1, col2 = st.columns(2)
    with col1:
        top_n = st.slider("Numero di Singole da mostrare", 1, 10, 5)
    with col2:
        max_s_odd = st.slider("Quota Massima Singola", 1.50, 5.00, 3.50)

    if st.button("🔍 Calcola Singole con Ollama"):
        with st.spinner("Elaborazione singole e analisi Ollama..."):
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
                            st.markdown("### 🤖 Valutazione Ollama")
                            ai_op = analyze_with_ollama(s['match'], s['selection'], s['odds'], s['prob_est'], s['ev'])
                            st.info(ai_op)
            else:
                st.warning("Nessuna singola trovata.")

with tab2:
    st.header("Generatore Schedina Multipla")
    cm1, cm2 = st.columns(2)
    with cm1:
        min_acc_odd = st.number_input("Quota Totale Minima", min_value=1.5, max_value=50.0, value=2.0, step=0.5)
        max_acc_odd = st.number_input("Quota Totale Massima", min_value=2.0, max_value=100.0, value=15.0, step=1.0)
    with cm2:
        min_ev_cnt = st.slider("Numero Minimo Eventi", 2, 6, 2)
        max_ev_cnt = st.slider("Numero Massimo Eventi", 2, 10, 5)

    if st.button("🎯 Genera Multipla Ottimale"):
        with st.spinner("Calcolo combinazioni ad alta probabilità..."):
            acc = build_accumulator(
                target_min_odds=float(min_acc_odd), 
                target_max_odds=float(max_acc_odd), 
                min_events=int(min_ev_cnt), 
                max_events=int(max_ev_cnt)
            )
            if acc:
                st.success(f"🎯 Multipla Trovata! Quota Totale: {acc['total_odds']} | Probabilità Combinata: {acc['combined_prob']}%")
                df_acc = pd.DataFrame(acc["events"])
                st.dataframe(df_acc[["league", "match", "selection", "odds", "prob", "ev"]], use_container_width=True)
            else:
                st.error("Nessuna combinazione soddisfa esattamente le quote inserite. Prova ad abbassare la Quota Minima (es. 2.0) o ad aumentare il range degli eventi.")

with tab3:
    st.header("Performance Reali Bankroll")
    summary = get_performance_summary()
    st.json(summary)